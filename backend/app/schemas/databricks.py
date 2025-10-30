from typing import Optional, List
from pydantic import BaseModel


class CatalogInfo(BaseModel):
    name: str
    comment: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    table_count: Optional[int] = 0
    schema_count: Optional[int] = 0


class SchemaInfo(BaseModel):
    catalog_name: str
    name: str
    full_name: str
    comment: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    table_count: Optional[int] = 0


class TableInfo(BaseModel):
    catalog_name: str
    schema_name: str
    name: str
    full_name: str
    table_type: Optional[str] = None
    comment: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    column_count: Optional[int] = 0
    row_count: Optional[int] = None


class ColumnInfo(BaseModel):
    catalog_name: str
    schema_name: str
    table_name: str
    name: str
    full_name: str
    data_type: str
    comment: Optional[str] = None
    nullable: bool = True
    partition_index: Optional[int] = None
    position: Optional[int] = None


class EntityPath(BaseModel):
    catalog: str
    schema: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None

    @property
    def full_path(self) -> str:
        path = self.catalog
        if self.schema:
            path += f".{self.schema}"
        if self.table:
            path += f".{self.table}"
        if self.column:
            path += f".{self.column}"
        return path


# Response wrapper models
class CatalogsResponse(BaseModel):
    catalogs: List[CatalogInfo]


class CatalogResponse(BaseModel):
    catalog: CatalogInfo


class SchemasResponse(BaseModel):
    schemas: List[SchemaInfo]


class TablesResponse(BaseModel):
    tables: List[TableInfo]


class ColumnsResponse(BaseModel):
    columns: List[ColumnInfo]