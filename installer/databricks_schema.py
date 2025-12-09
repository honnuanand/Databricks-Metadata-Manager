"""
Databricks Unity Catalog schema management for Metadata Manager installer.

Handles creation and verification of:
- Schemas
- Tables
- Views
- Seed data
- Permission grants
"""

import subprocess
import json
import time
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TableDefinition:
    """Definition of a table to create"""
    name: str
    columns: str
    comment: str
    partitioned_by: Optional[str] = None


@dataclass
class SQLResult:
    """Result of SQL execution"""
    success: bool
    message: str
    data: Optional[List[Dict]] = None


class DatabricksSchemaManager:
    """Manages Databricks Unity Catalog schemas and tables"""

    # Table definitions for metadata_manager schema
    METADATA_MANAGER_TABLES = [
        TableDefinition(
            name="users",
            columns="""
                user_id STRING NOT NULL,
                username STRING NOT NULL,
                email STRING NOT NULL,
                full_name STRING,
                role STRING NOT NULL,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            """,
            comment="System users with role-based access for metadata management"
        ),
        TableDefinition(
            name="comment_suggestions",
            columns="""
                suggestion_id STRING NOT NULL,
                entity_type STRING NOT NULL,
                entity_catalog STRING NOT NULL,
                entity_schema STRING,
                entity_table STRING,
                entity_column STRING,
                entity_full_path STRING NOT NULL,
                current_comment STRING,
                suggested_comment STRING NOT NULL,
                status STRING NOT NULL,
                created_by STRING NOT NULL,
                approved_by STRING,
                submitted_at TIMESTAMP,
                approved_at TIMESTAMP,
                applied_at TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            """,
            comment="Central repository tracking all metadata comment suggestions"
        ),
        TableDefinition(
            name="approvals",
            columns="""
                approval_id STRING NOT NULL,
                suggestion_id STRING NOT NULL,
                approver_id STRING NOT NULL,
                action STRING NOT NULL,
                feedback STRING,
                created_at TIMESTAMP
            """,
            comment="Complete history of all approval actions on comment suggestions"
        ),
        TableDefinition(
            name="audit_logs",
            columns="""
                log_id STRING NOT NULL,
                user_id STRING,
                username STRING,
                action STRING NOT NULL,
                entity_type STRING,
                entity_id STRING,
                entity_path STRING,
                details STRING,
                ip_address STRING,
                user_agent STRING,
                created_at TIMESTAMP
            """,
            comment="Comprehensive audit trail for all system activities"
        ),
    ]

    # Table definitions for metadata_test schema
    METADATA_TEST_TABLES = [
        TableDefinition(
            name="users",
            columns="""
                user_id BIGINT COMMENT 'Unique identifier for each user',
                email STRING COMMENT 'User email address for login and notifications',
                first_name STRING COMMENT 'User first name',
                last_name STRING COMMENT 'User last name',
                phone STRING COMMENT 'User phone number for contact',
                address STRING COMMENT 'User billing address',
                city STRING COMMENT 'User city',
                state STRING COMMENT 'User state or province',
                zip_code STRING COMMENT 'User postal/zip code',
                country STRING COMMENT 'User country',
                registration_date DATE COMMENT 'Date when user registered',
                last_login TIMESTAMP COMMENT 'Timestamp of users last login',
                is_active BOOLEAN COMMENT 'Whether user account is active',
                total_orders INT COMMENT 'Total number of orders placed by user',
                total_spent DECIMAL(10,2) COMMENT 'Total amount spent by user'
            """,
            comment="Customer information and profile data"
        ),
        TableDefinition(
            name="products",
            columns="""
                product_id BIGINT COMMENT 'Unique product identifier',
                sku STRING COMMENT 'Stock keeping unit - unique product code',
                product_name STRING COMMENT 'Display name of the product',
                category STRING COMMENT 'Product category (Electronics, Clothing, etc.)',
                subcategory STRING COMMENT 'Product subcategory for finer classification',
                brand STRING COMMENT 'Brand or manufacturer name',
                description STRING COMMENT 'Detailed product description',
                price DECIMAL(10,2) COMMENT 'Current selling price of the product',
                cost DECIMAL(10,2) COMMENT 'Cost to acquire/manufacture the product',
                weight DECIMAL(8,3) COMMENT 'Product weight in pounds',
                dimensions STRING COMMENT 'Product dimensions (LxWxH)',
                color STRING COMMENT 'Primary color of the product',
                size STRING COMMENT 'Size specification (S/M/L, numeric, etc.)',
                inventory_count INT COMMENT 'Current stock level',
                reorder_level INT COMMENT 'Minimum stock level before reordering',
                supplier_id INT COMMENT 'Reference to supplier providing this product',
                created_date DATE COMMENT 'Date product was added to catalog',
                last_updated TIMESTAMP COMMENT 'Last time product info was updated',
                is_active BOOLEAN COMMENT 'Whether product is currently available for sale'
            """,
            comment="Product catalog with detailed item specifications and inventory"
        ),
        TableDefinition(
            name="orders",
            columns="""
                order_id BIGINT COMMENT 'Unique order identifier',
                user_id BIGINT COMMENT 'Reference to user who placed the order',
                order_date TIMESTAMP COMMENT 'When the order was placed',
                order_status STRING COMMENT 'Current status: pending, processing, shipped, delivered, cancelled',
                payment_method STRING COMMENT 'How customer paid: credit_card, paypal, bank_transfer',
                payment_status STRING COMMENT 'Payment status: pending, completed, failed, refunded',
                subtotal DECIMAL(10,2) COMMENT 'Order subtotal before taxes and shipping',
                tax_amount DECIMAL(8,2) COMMENT 'Total tax amount charged',
                shipping_cost DECIMAL(8,2) COMMENT 'Shipping and handling charges',
                discount_amount DECIMAL(8,2) COMMENT 'Total discounts applied',
                total_amount DECIMAL(10,2) COMMENT 'Final total amount charged',
                shipping_address STRING COMMENT 'Address where order should be shipped',
                billing_address STRING COMMENT 'Billing address for payment',
                tracking_number STRING COMMENT 'Shipping tracking number',
                shipped_date DATE COMMENT 'Date order was shipped',
                delivered_date DATE COMMENT 'Date order was delivered',
                notes STRING COMMENT 'Special instructions or notes'
            """,
            comment="Customer orders with payment and shipping details"
        ),
        TableDefinition(
            name="order_items",
            columns="""
                order_item_id BIGINT COMMENT 'Unique identifier for order line item',
                order_id BIGINT COMMENT 'Reference to parent order',
                product_id BIGINT COMMENT 'Reference to ordered product',
                quantity INT COMMENT 'Number of units ordered',
                unit_price DECIMAL(10,2) COMMENT 'Price per unit at time of order',
                total_price DECIMAL(10,2) COMMENT 'Total price for this line item',
                discount_applied DECIMAL(8,2) COMMENT 'Discount amount applied to this item',
                product_name STRING COMMENT 'Product name at time of order (for historical record)',
                sku STRING COMMENT 'Product SKU at time of order'
            """,
            comment="Individual line items within customer orders"
        ),
        TableDefinition(
            name="employees",
            columns="""
                employee_id INT COMMENT 'Unique employee identifier',
                employee_number STRING COMMENT 'Human-readable employee number',
                first_name STRING COMMENT 'Employee first name',
                last_name STRING COMMENT 'Employee last name',
                email STRING COMMENT 'Corporate email address',
                phone STRING COMMENT 'Work phone number',
                department STRING COMMENT 'Department: Engineering, Sales, Marketing, HR, Finance',
                job_title STRING COMMENT 'Current job title or position',
                manager_id INT COMMENT 'Employee ID of direct manager',
                hire_date DATE COMMENT 'Date employee was hired',
                salary DECIMAL(10,2) COMMENT 'Current annual salary',
                bonus_eligible BOOLEAN COMMENT 'Whether employee is eligible for bonuses',
                employment_status STRING COMMENT 'Employment status: active, terminated, on_leave',
                office_location STRING COMMENT 'Primary office location',
                remote_work_eligible BOOLEAN COMMENT 'Whether employee can work remotely',
                performance_rating DECIMAL(2,1) COMMENT 'Latest performance rating (1-5 scale)',
                last_promotion_date DATE COMMENT 'Date of most recent promotion',
                benefits_tier STRING COMMENT 'Benefits package tier: basic, premium, executive'
            """,
            comment="Employee master data with HR and payroll information"
        ),
        TableDefinition(
            name="customer_segments",
            columns="""
                user_id BIGINT COMMENT 'Reference to user',
                segment STRING COMMENT 'Customer segment: VIP, Regular, New, At_Risk, Churned',
                ltv DECIMAL(10,2) COMMENT 'Customer lifetime value',
                avg_order_value DECIMAL(8,2) COMMENT 'Average order value for this customer',
                order_frequency DECIMAL(5,2) COMMENT 'Average days between orders',
                last_order_date DATE COMMENT 'Date of most recent order',
                predicted_churn_probability DECIMAL(3,2) COMMENT 'Probability of customer churning (0-1)',
                segment_assigned_date DATE COMMENT 'When customer was assigned to current segment',
                preferred_category STRING COMMENT 'Customers most purchased category',
                communication_preference STRING COMMENT 'How customer prefers to be contacted'
            """,
            comment="Customer segmentation data for marketing and retention analysis"
        ),
        TableDefinition(
            name="daily_sales_summary",
            columns="""
                date DATE COMMENT 'Date of sales data',
                total_orders INT COMMENT 'Number of orders placed on this date',
                total_revenue DECIMAL(12,2) COMMENT 'Total revenue generated on this date',
                total_units_sold INT COMMENT 'Total number of items sold',
                average_order_value DECIMAL(10,2) COMMENT 'Average order value for this date',
                new_customers INT COMMENT 'Number of first-time customers',
                returning_customers INT COMMENT 'Number of returning customers',
                top_category STRING COMMENT 'Best selling product category',
                top_product STRING COMMENT 'Best selling individual product'
            """,
            comment="Daily aggregated sales metrics for reporting and analysis"
        ),
        TableDefinition(
            name="revenue_by_product",
            columns="""
                product_id BIGINT COMMENT 'Reference to product',
                year INT COMMENT 'Revenue year',
                quarter INT COMMENT 'Revenue quarter (1-4)',
                month INT COMMENT 'Revenue month (1-12)',
                units_sold INT COMMENT 'Total units sold in period',
                gross_revenue DECIMAL(12,2) COMMENT 'Total revenue before returns/discounts',
                net_revenue DECIMAL(12,2) COMMENT 'Revenue after returns and discounts',
                cost_of_goods_sold DECIMAL(12,2) COMMENT 'Total cost to produce/acquire sold units',
                gross_profit DECIMAL(12,2) COMMENT 'Gross profit (net_revenue - cogs)',
                profit_margin DECIMAL(5,4) COMMENT 'Profit margin percentage',
                return_rate DECIMAL(4,3) COMMENT 'Percentage of units returned',
                discount_rate DECIMAL(4,3) COMMENT 'Average discount rate applied'
            """,
            comment="Product revenue analysis with profitability metrics"
        ),
    ]

    # Seed data for users table
    SEED_USERS = [
        ("u001", "john_suggest", "john.suggest@example.com", "John Doe", "suggest_only", True),
        ("u002", "jane_approver", "jane.approver@example.com", "Jane Smith", "approver", True),
        ("u003", "admin_user", "admin@example.com", "Admin User", "admin", True),
        ("u004", "alice_suggest", "alice.suggest@example.com", "Alice Johnson", "suggest_only", True),
        ("u005", "bob_approver", "bob.approver@example.com", "Bob Williams", "approver", True),
    ]

    def __init__(self, warehouse_id: str, verbose: bool = False):
        self.warehouse_id = warehouse_id
        self.verbose = verbose

    def run_command(self, command: List[str]) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=120
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    def execute_sql(self, statement: str) -> SQLResult:
        """Execute a SQL statement via Databricks CLI"""
        # Use statement execution API
        exit_code, stdout, stderr = self.run_command([
            "databricks", "sql", "execute",
            "--warehouse-id", self.warehouse_id,
            "--statement", statement,
            "--output", "json"
        ])

        if exit_code != 0:
            return SQLResult(success=False, message=stderr or "SQL execution failed")

        try:
            result = json.loads(stdout) if stdout.strip() else {}
            return SQLResult(success=True, message="OK", data=result.get("data_array", []))
        except json.JSONDecodeError:
            return SQLResult(success=True, message="OK")

    def ensure_warehouse_running(self) -> Tuple[bool, str]:
        """Ensure the SQL warehouse is running"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "warehouses", "get", self.warehouse_id, "--output", "json"
        ])

        if exit_code != 0:
            return False, f"Cannot access warehouse: {stderr}"

        try:
            info = json.loads(stdout)
            state = info.get("state", "")

            if state == "RUNNING":
                return True, "Warehouse is running"

            if state == "STOPPED":
                # Start the warehouse
                exit_code, stdout, stderr = self.run_command([
                    "databricks", "warehouses", "start", self.warehouse_id
                ])

                if exit_code != 0:
                    return False, f"Failed to start warehouse: {stderr}"

                # Wait for it to start
                for _ in range(60):  # Wait up to 5 minutes
                    time.sleep(5)
                    exit_code, stdout, stderr = self.run_command([
                        "databricks", "warehouses", "get", self.warehouse_id, "--output", "json"
                    ])
                    if exit_code == 0:
                        info = json.loads(stdout)
                        if info.get("state") == "RUNNING":
                            return True, "Warehouse started"

                return False, "Warehouse failed to start in time"

            return False, f"Warehouse in unexpected state: {state}"

        except json.JSONDecodeError:
            return False, "Invalid warehouse response"

    def check_schema_exists(self, catalog: str, schema: str) -> bool:
        """Check if a schema exists"""
        result = self.execute_sql(f"SHOW SCHEMAS IN {catalog} LIKE '{schema}'")
        return result.success and result.data and len(result.data) > 0

    def check_table_exists(self, catalog: str, schema: str, table: str) -> bool:
        """Check if a table exists"""
        result = self.execute_sql(f"SHOW TABLES IN {catalog}.{schema} LIKE '{table}'")
        return result.success and result.data and len(result.data) > 0

    def create_schema(self, catalog: str, schema: str, comment: str, skip_existing: bool = True) -> SQLResult:
        """Create a schema"""
        if skip_existing and self.check_schema_exists(catalog, schema):
            return SQLResult(success=True, message=f"Schema {catalog}.{schema} already exists (skipped)")

        sql = f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} COMMENT '{comment}'"
        result = self.execute_sql(sql)

        if result.success:
            return SQLResult(success=True, message=f"Created schema {catalog}.{schema}")
        return result

    def create_table(self, catalog: str, schema: str, table_def: TableDefinition, skip_existing: bool = True) -> SQLResult:
        """Create a table"""
        full_name = f"{catalog}.{schema}.{table_def.name}"

        if skip_existing and self.check_table_exists(catalog, schema, table_def.name):
            return SQLResult(success=True, message=f"Table {full_name} already exists (skipped)")

        # Clean up column definitions
        columns = table_def.columns.strip().replace('\n', ' ').replace('  ', ' ')

        sql = f"CREATE TABLE IF NOT EXISTS {full_name} ({columns}) COMMENT '{table_def.comment}'"

        if table_def.partitioned_by:
            sql += f" PARTITIONED BY ({table_def.partitioned_by})"

        result = self.execute_sql(sql)

        if result.success:
            return SQLResult(success=True, message=f"Created table {full_name}")
        return result

    def insert_seed_users(self, catalog: str, schema: str) -> SQLResult:
        """Insert seed users into the users table"""
        full_table = f"{catalog}.{schema}.users"

        # Check if users already exist
        result = self.execute_sql(f"SELECT COUNT(*) as cnt FROM {full_table}")
        if result.success and result.data:
            try:
                count = int(result.data[0][0]) if result.data[0] else 0
                if count > 0:
                    return SQLResult(success=True, message=f"Users table already has {count} records (skipped)")
            except (IndexError, ValueError):
                pass

        # Insert seed users
        values = []
        for user in self.SEED_USERS:
            user_id, username, email, full_name, role, is_active = user
            values.append(f"('{user_id}', '{username}', '{email}', '{full_name}', '{role}', {str(is_active).lower()}, current_timestamp(), current_timestamp())")

        sql = f"""
            INSERT INTO {full_table} (user_id, username, email, full_name, role, is_active, created_at, updated_at)
            VALUES {', '.join(values)}
        """

        result = self.execute_sql(sql)
        if result.success:
            return SQLResult(success=True, message=f"Inserted {len(self.SEED_USERS)} seed users")
        return result

    def grant_permissions(self, catalog: str, schema_primary: str, schema_test: str, service_principal: str) -> List[SQLResult]:
        """Grant all required permissions to service principal"""
        results = []

        grants = [
            f"GRANT USE CATALOG ON CATALOG {catalog} TO `{service_principal}`",
            f"GRANT USE SCHEMA ON SCHEMA {catalog}.{schema_primary} TO `{service_principal}`",
            f"GRANT USE SCHEMA ON SCHEMA {catalog}.{schema_test} TO `{service_principal}`",
            f"GRANT SELECT ON SCHEMA {catalog}.{schema_test} TO `{service_principal}`",
            f"GRANT ALL PRIVILEGES ON SCHEMA {catalog}.{schema_primary} TO `{service_principal}`",
        ]

        for grant_sql in grants:
            result = self.execute_sql(grant_sql)
            if result.success:
                results.append(SQLResult(success=True, message=f"Executed: {grant_sql[:50]}..."))
            else:
                results.append(SQLResult(success=False, message=f"Failed: {grant_sql[:50]}... - {result.message}"))

        return results

    def setup_all_schemas(
        self,
        catalog: str,
        schema_primary: str = "metadata_manager",
        schema_test: str = "metadata_test",
        create_test_schema: bool = True,
        skip_existing: bool = True,
        dry_run: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Set up all schemas, tables, and seed data.

        Returns:
            Tuple of (success, list of messages)
        """
        messages = []

        if dry_run:
            messages.append(f"[DRY RUN] Would create schema: {catalog}.{schema_primary}")
            messages.append(f"[DRY RUN] Would create {len(self.METADATA_MANAGER_TABLES)} tables in {schema_primary}")
            if create_test_schema:
                messages.append(f"[DRY RUN] Would create schema: {catalog}.{schema_test}")
                messages.append(f"[DRY RUN] Would create {len(self.METADATA_TEST_TABLES)} tables in {schema_test}")
            return True, messages

        # Ensure warehouse is running
        success, msg = self.ensure_warehouse_running()
        messages.append(msg)
        if not success:
            return False, messages

        # Create metadata_manager schema
        result = self.create_schema(catalog, schema_primary, "Central repository for Databricks metadata management", skip_existing)
        messages.append(result.message)
        if not result.success:
            return False, messages

        # Create metadata_manager tables
        for table_def in self.METADATA_MANAGER_TABLES:
            result = self.create_table(catalog, schema_primary, table_def, skip_existing)
            messages.append(result.message)
            if not result.success:
                return False, messages

        # Insert seed users
        result = self.insert_seed_users(catalog, schema_primary)
        messages.append(result.message)

        # Create test schema if requested
        if create_test_schema:
            result = self.create_schema(catalog, schema_test, "Test data for metadata manager application", skip_existing)
            messages.append(result.message)
            if not result.success:
                return False, messages

            # Create test tables
            for table_def in self.METADATA_TEST_TABLES:
                result = self.create_table(catalog, schema_test, table_def, skip_existing)
                messages.append(result.message)
                if not result.success:
                    return False, messages

        return True, messages

    def verify_schema_structure(self, catalog: str, schema: str) -> Dict[str, bool]:
        """Verify that all expected tables exist in a schema"""
        expected_tables = []
        if schema == "metadata_manager":
            expected_tables = [t.name for t in self.METADATA_MANAGER_TABLES]
        elif schema == "metadata_test":
            expected_tables = [t.name for t in self.METADATA_TEST_TABLES]

        verification = {}
        for table in expected_tables:
            verification[table] = self.check_table_exists(catalog, schema, table)

        return verification
