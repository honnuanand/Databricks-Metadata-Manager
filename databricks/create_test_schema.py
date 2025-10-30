#!/usr/bin/env python3

"""
Create test schema with sample tables and comments for testing metadata manager functionality.
This creates a comprehensive test environment with various table types, columns, and comments.
"""

import os
from databricks import sql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Databricks connection parameters
SERVER_HOSTNAME = "e2-demo-field-eng.cloud.databricks.com"
HTTP_PATH = "/sql/1.0/warehouses/00887ae543d50e2a"

def get_connection():
    """Create a connection to Databricks"""
    token = os.getenv("DATABRICKS_TOKEN")
    if not token:
        raise ValueError("DATABRICKS_TOKEN environment variable is required")
    
    return sql.connect(
        server_hostname=SERVER_HOSTNAME,
        http_path=HTTP_PATH,
        access_token=token
    )

def create_test_schema_and_tables():
    """Create test schema with comprehensive sample data"""
    
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        # Create the test schema
        logger.info("Creating metadata_test schema...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS arao.metadata_test")
        
        # E-commerce sample tables
        logger.info("Creating e-commerce sample tables...")
        
        # Users table
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.users (
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
            ) COMMENT 'Customer information and profile data'
        """)
        
        # Products table
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.products (
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
            ) COMMENT 'Product catalog with detailed item specifications and inventory'
        """)
        
        # Orders table
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.orders (
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
            ) COMMENT 'Customer orders with payment and shipping details'
        """)
        
        # Order Items table
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.order_items (
                order_item_id BIGINT COMMENT 'Unique identifier for order line item',
                order_id BIGINT COMMENT 'Reference to parent order',
                product_id BIGINT COMMENT 'Reference to ordered product',
                quantity INT COMMENT 'Number of units ordered',
                unit_price DECIMAL(10,2) COMMENT 'Price per unit at time of order',
                total_price DECIMAL(10,2) COMMENT 'Total price for this line item (quantity * unit_price)',
                discount_applied DECIMAL(8,2) COMMENT 'Discount amount applied to this item',
                product_name STRING COMMENT 'Product name at time of order (for historical record)',
                sku STRING COMMENT 'Product SKU at time of order'
            ) COMMENT 'Individual line items within customer orders'
        """)
        
        # Analytics and reporting tables
        logger.info("Creating analytics sample tables...")
        
        # Daily Sales Summary
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.daily_sales_summary (
                date DATE COMMENT 'Date of sales data',
                total_orders INT COMMENT 'Number of orders placed on this date',
                total_revenue DECIMAL(12,2) COMMENT 'Total revenue generated on this date',
                total_units_sold INT COMMENT 'Total number of items sold',
                average_order_value DECIMAL(10,2) COMMENT 'Average order value for this date',
                new_customers INT COMMENT 'Number of first-time customers',
                returning_customers INT COMMENT 'Number of returning customers',
                top_category STRING COMMENT 'Best selling product category',
                top_product STRING COMMENT 'Best selling individual product'
            ) COMMENT 'Daily aggregated sales metrics for reporting and analysis'
        """)
        
        # Customer Segments
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.customer_segments (
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
            ) COMMENT 'Customer segmentation data for marketing and retention analysis'
        """)
        
        # HR/Employee sample tables
        logger.info("Creating HR sample tables...")
        
        # Employees
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.employees (
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
            ) COMMENT 'Employee master data with HR and payroll information'
        """)
        
        # Financial sample tables
        logger.info("Creating financial sample tables...")
        
        # Revenue by Product
        cursor.execute("""
            CREATE OR REPLACE TABLE arao.metadata_test.revenue_by_product (
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
            ) COMMENT 'Product revenue analysis with profitability metrics'
        """)
        
        logger.info("Test schema and tables created successfully!")
        logger.info("Created the following tables in arao.metadata_test:")
        logger.info("- users: Customer information")
        logger.info("- products: Product catalog") 
        logger.info("- orders: Customer orders")
        logger.info("- order_items: Order line items")
        logger.info("- daily_sales_summary: Daily sales metrics")
        logger.info("- customer_segments: Customer segmentation")
        logger.info("- employees: HR employee data")
        logger.info("- revenue_by_product: Financial revenue analysis")
        
    except Exception as e:
        logger.error(f"Error creating test schema: {e}")
        raise
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    create_test_schema_and_tables()