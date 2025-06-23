from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.company import Company
from app.models.processed_feature import ProcessedFeature
from app.models.rule import Condition, Rule
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleOut
from app.services.rule_processor import process_rule

router = APIRouter()


@router.post(
    "/create_rule", response_model=RuleOut, status_code=status.HTTP_201_CREATED
)
async def create_rule(payload: RuleCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates one or more rules for a user. If the user doesn't exist, creates
    the user.

    Args:
        payload (dict): JSON containing the user_name and a list of rules.
        db (AsyncSession): The database session.

    Returns:
        dict: Summary of the created rules.
    """

    if not payload.user_name or not payload.rules:
        raise HTTPException(
            status_code=400, detail="Missing user_name or rules"
        )

    user_result = await db.execute(
        select(User).where(User.user_name == payload.user_name)
    )
    user = user_result.scalars().first()

    if not user:
        user = User(user_name=payload.user_name)
        db.add(user)
        await db.flush()

    created_rules = []

    for rule in payload.rules:
        operation_block = rule.get("operation", {})
        if not isinstance(operation_block, dict):
            raise HTTPException(
                status_code=400, detail="Invalid operation block"
            )
        conditions: list[dict] = []
        if (operator := list(operation_block.keys())[0].upper()) in (
            "AND",
            "OR",
        ):
            bool_op = operator
            conditions = operation_block.get(operator, {})
        elif isinstance(operation_block, list) and list(
            operation_block.keys()
        )[0].upper() not in (
            "AND",
            "OR",
        ):
            raise HTTPException(
                status_code=400, detail="Invalid boolean operator"
            )
        else:
            bool_op = None
            conditions = [operation_block]
        conditions_list = []
        for cond in conditions:
            if not isinstance(cond, dict):
                raise HTTPException(
                    status_code=400, detail="Invalid condition format"
                )
            new_condition = Condition(
                operator=cond.get("operator"),
                target_object=cond.get("target_object"),
                value=str(cond.get("value")),
                rule_id=None,
            )
            conditions_list.append(new_condition)

        new_rule = Rule(
            input=rule.get("input"),
            feature_name=rule.get("feature_name"),
            match=rule.get("match", 0),
            default=rule.get("default", 0),
            user_id=user.id,
            conditions=conditions_list,
            boolean_operator=bool_op,
        )

        # check if the rule already exists
        existing_rule = await db.execute(
            select(Rule).where(
                Rule.input == new_rule.input,
                Rule.feature_name == new_rule.feature_name,
                Rule.user_id == user.id,
            )
        )
        if existing_rule.scalars().first():
            continue
        db.add(new_rule)

        created_rules.append(
            {
                "input": new_rule.input,
                "feature_name": new_rule.feature_name,
                "match": new_rule.match,
                "default": new_rule.default,
                "boolean_operator": bool_op or "N/A",
                "conditions": conditions,
            }
        )

    await db.commit()

    return RuleOut(
        success=True,
        message="Rule created successfully",
        rule={
            "user_name": payload.user_name,
            "rules": created_rules,
        },
    )


@router.post("/process_companies")
async def process_companies(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Processes a list of companies for a given user by applying all their rules.

    Args:
        payload (dict): Contains user_name and list of company URLs.
        db (AsyncSession): Async database session.

    Returns:
        list[dict]: A list of processed companies and their feature
        evaluations.
    """
    user_name = payload.get("user_name")
    urls = payload.get("urls")

    if not user_name or not urls:
        raise HTTPException(
            status_code=400, detail="Missing user_name or urls"
        )

    user_result = await db.execute(
        select(User).options(selectinload(User.rules))
    )
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    companies_result = await db.execute(
        select(Company).where(Company.url.in_(urls))
    )
    companies = companies_result.scalars().all()

    if not companies:
        raise HTTPException(status_code=404, detail="No companies found")

    rules_result = await db.execute(
        select(Rule)
        .options(selectinload(Rule.conditions))
        .where(Rule.user_id == user.id)
    )
    rules = rules_result.scalars().all()

    if isinstance(rules, Rule):
        rules = [rules]

    output = []

    for company in companies:
        result = {"company": company.name}
        for rule in rules:
            try:
                rule_result = await process_rule(rule, company)

                result[rule.feature_name] = (
                    rule.match if rule_result else rule.default
                )
            except Exception as e:
                raise e
            db.add(
                ProcessedFeature(
                    company_id=company.id,
                    rule_id=rule.id,
                    user_id=rule.user_id,
                    feature_name=rule.feature_name,
                    value=rule_result,
                )
            )
        company.last_processed_at = datetime.now(UTC).replace(tzinfo=None)
        db.add(company)

        output.append(result)
    await db.commit()

    return output
