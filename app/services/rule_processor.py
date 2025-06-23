import json
import os
from operator import attrgetter

import httpx

from app.models.company import Company
from app.models.rule import Rule


async def process_llm(question: str, context: str) -> bool:
    prompt = f"""Context:
    {context}

    Question: {question}
    Answer with "true" or "false" only.
    """
    response = httpx.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
        ),
    )
    choices = response.json().get("choices", [])
    if choices:
        return (
            choices[0].get("message", {}).get("text", "").strip().lower()
            == "true"
        )
    return False


async def evaluate_condition(condition, value):
    """
    Evaluates a single condition against a value.

    Args:
        condition (Condition): The condition to evaluate.
        value (any): The value to compare against the condition.

    Returns:
        bool: True if the condition is met, False otherwise.
    """
    match condition.operator:
        case "EQUALS":
            return value == condition.value
        case "NOT_EQUALS":
            return value != condition.value
        case "GREATER_THAN":
            return float(value) > float(condition.value)
        case "LESS_THAN":
            return float(value) < float(condition.value)
        case "CONTAINS":
            return condition.value in str(value)
        case "NOT_CONTAINS":
            return condition.value not in str(value)
        case "LLM":
            # For LLM conditions, we need to process the question and context
            question = condition.value
            context = f"{condition.target_object}: {value}"
            return await process_llm(question, context)
        case _:
            return False  # Unsupported operator


async def process_rule(rule: Rule, company: Company) -> bool:
    """
    Processes a rule against a company object to determine if it matches the
    conditions defined in the rule.

    Args:
        rule (Rule): The rule to be processed.
        company (Company): The company object to evaluate against the rule.

    Returns:
        bool: True if the company matches the rule, False otherwise.
    """
    conditions = rule.conditions
    if len(conditions) == 1:
        attr_value = attrgetter(conditions[0].target_object)(company)
        return await evaluate_condition(conditions[0], attr_value)

    conditions_results = []
    for condition in conditions:
        attr_value = attrgetter(condition.target_object)(company)
        conditions_results.append(
            await evaluate_condition(condition, attr_value)
        )
    if rule.boolean_operator == "AND":
        return all(conditions_results)
    elif rule.boolean_operator == "OR":
        return any(conditions_results)
    else:
        raise ValueError(
            f"Unsupported boolean operator: {rule.boolean_operator}"
        )
