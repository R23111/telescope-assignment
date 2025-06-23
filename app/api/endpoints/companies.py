"""
API endpoint for importing company data into the database.
"""

import csv

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.company import Company
from app.models.processed_feature import ProcessedFeature
from app.schemas.company import CompanyCreate, CompanyOut, ImportSummary
from app.schemas.processed_feature import ProcessedFeatureOut
from app.utils.logger import logger

router = APIRouter()


@router.post("/import_company_data", response_model=ImportSummary)
async def import_company_data(
    file: UploadFile = File(None),
    json_data: list[CompanyCreate] | None = Body(None),
    db: AsyncSession = Depends(get_db),
) -> ImportSummary:
    """
    Imports company data from a CSV file or JSON payload into the database.

    This endpoint processes uploaded company data, checks for duplicates, and
    adds new records to the database. It returns a summary of the import
    operation.

    Args:
        file (UploadFile, optional): The CSV file containing company data.
        json_data (list[CompanyCreate], optional): A list of company data in
        JSON format.
        db (AsyncSession): The database session dependency.

    Returns:
        ImportSummary: A summary of the import results, including counts of
        imported records, duplicates, and errors.
    """
    companies: list[CompanyCreate] = []

    if file is not None:
        content = await file.read()
        reader = csv.DictReader(content.decode("utf-8").splitlines())
        companies = [CompanyCreate.from_csv_row(row) for row in reader]
    elif json_data is not None:
        companies = json_data
    else:
        raise HTTPException(status_code=400, detail="No data provided")

    imported = 0
    skipped_duplicates = 0
    record_errors = 0
    errors: list[str] = []
    for company in companies:
        try:
            existing = await db.execute(
                select(Company).where(Company.url == company.url)
            )
            if existing.scalar_one_or_none():
                skipped_duplicates += 1
                continue
            db_company = Company(**company.model_dump())
            db.add(db_company)
            imported += 1
        except Exception as e:
            record_errors += 1
            errors.append(company.name)
            logger.warning(f"Error importing company {company.name}: {e}")

    await db.commit()
    return ImportSummary(
        imported_records=imported,
        skipped_duplicates=skipped_duplicates,
        record_errors=record_errors,
        errors=errors,
    )


@router.get("/get_companies", response_model=list[CompanyOut])
async def get_companies(db: AsyncSession = Depends(get_db)):
    """
    Returns a list of all imported companies with their raw data and processed
    features.

    Returns:
        List of CompanyOut: JSON list of company data and processing metadata.
    """
    result = await db.execute(
        select(Company).options(
            selectinload(Company.processed_features).selectinload(
                ProcessedFeature.rule
            ),
            selectinload(Company.processed_features).selectinload(
                ProcessedFeature.user
            ),
        )
    )

    return [
        CompanyOut(
            id=res.id,
            url=res.url,
            data={
                c.key: getattr(res, c.key)
                for c in inspect(res).mapper.column_attrs
                if c.key
                not in [
                    "id",
                    "imported_at",
                    "last_processed_at",
                ]
            },
            processed_features=[
                ProcessedFeatureOut(
                    user_name=pf.user.user_name,
                    company_name=res.name,
                    feature_name=pf.feature_name,
                    value=pf.value,
                )
                for pf in res.processed_features
            ],
            imported_at=res.imported_at,
            last_processed_at=res.last_processed_at,
        )
        for res in result.scalars().all()
    ]
