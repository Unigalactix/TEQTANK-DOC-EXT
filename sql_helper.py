from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# T-SQL Database Schema
DATABASE_SCHEMA = """
-- Table: ttvCommissionDetails
-- Description: Contains individual records for each commission payout line item.
-- Columns:
--   - PeriodType (INT): The type of the period.
--   - PeriodTypeDescr (NVARCHAR): VALID VALUES: ['Weekly', 'Monthly'].
--   - PeriodId (INT): The ID of the specific period.
--   - PeriodIdDescr (NVARCHAR): Description of the period (e.g. 'Week 50 12/6-12/12 2025').
--   - BonusId (INT): The ID of the bonus that generated this commission.
--   - BonusIdDescr (NVARCHAR): VALID VALUES include: ['First Order Customer Bonus', 'Team Rewards'].
--   - FromCustomerId (BIGINT): The customer whose activity generated the commission (the source).
--   - FromName (NVARCHAR): The name of the source customer.
--   - ToCustomerId (BIGINT): The customer receiving the commission (the earner).
--   - ToName (NVARCHAR): The name of the earning customer.
--   - OrderId (BIGINT): The order ID linked to this commission (if applicable).
--   - SourceAmount (MONEY): The base amount on which the commission was calculated.
--   - CommissionAmount (MONEY): The final commission payout amount.
--   - RunId (INT): The ID of the commission run. (0 = Pending/Preliminary, >0 = Paid/Final).
--   - CurrencyCode (NVARCHAR): The currency of the payout (e.g. 'usd').

-- Table: ttvCommissions
-- Description: A summary of total commissions earned per customer per period.
-- Columns:
--   - PeriodType (INT): The type of the period.
--   - PeriodTypeDescr (NVARCHAR): VALID VALUES: ['Weekly', 'Monthly'].
--   - CommissionId (INT): Unique ID for the commission record.
--   - CustomerId (BIGINT): The customer who earned the commissions.
--   - FirstName (NVARCHAR): The first name of the earner.
--   - LastName (NVARCHAR): The last name of the earner.
--   - CommissionAmount (MONEY): The total commission amount for the period.
--   - RunId (INT): The ID of the commission run. (0 = Pending/Preliminary, >0 = Paid/Final).

-- Table: ttvCustomers
-- Description: Stores all customer profile and lineage data.
-- Columns:
--   - CustomerId (BIGINT): The unique ID for the customer.
--   - CustomerType (INT): The type of customer.
--   - CustomerTypeDescr (NVARCHAR): VALID VALUES: ['Affiliate', 'Customer'].
--   - CustomerSubTypeDescr (NVARCHAR): VALID VALUES: ['Retail'].
--   - CustomerStatusTypeDescr (NVARCHAR): VALID VALUES: ['Commissionable'].
--   - CustomerSubStatusTypeDescr (NVARCHAR): VALID VALUES: ['Active', 'Cancelled'].
--   - RankId (INT): The customer's highest achieved rank ID.
--   - RankIdDescr (NVARCHAR): VALID VALUES: ['Affiliate', 'Bronze', 'Silver', 'Gold', 'Diamond'].
--   - EnrollerId (BIGINT): The ID of the customer who enrolled this customer (Enroller Tree Parent).
--   - EnrollerName (NVARCHAR): Name of the enroller.
--   - SponsorId (BIGINT): The ID of the parent in the Unilevel/Placement tree.
--   - BinaryParentId (BIGINT): The ID of the parent in the Binary tree.
--   - MatrixParentId (BIGINT): The ID of the parent in the Matrix tree.
--   - FirstName (NVARCHAR): The customer's legal first name.
--   - LastName (NVARCHAR): The customer's legal last name.
--   - SignUpDate (DATETIMEOFFSET): Date the customer originally signed up.
--   - EmailAddress (NVARCHAR): Primary email.

-- Table: ttvOrders
-- Description: Contains order header information.
-- Columns:
--   - OrderId (BIGINT): The unique ID for the order.
--   - CustomerId (BIGINT): The customer who placed the order.
--   - CustomerName (NVARCHAR): Name of the customer.
--   - OrderDate (DATETIMEOFFSET): Date the order was created.
--   - OrderTotal (MONEY): Total amount charged.
--   - QV (MONEY): Qualifying Volume (used for Ranks).
--   - CV (MONEY): Commissionable Volume (used for Payouts).
--   - IsCommissionable (BIT): 1 if eligible for commissions, 0 otherwise.
--   - OrderStatusTypeDescr (NVARCHAR): VALID VALUES: ['Approved', 'Cancelled', 'Pending']. (Note: 'Shipped' is NOT a valid status).
--   - OrderSubStatusTypeDescr (NVARCHAR): VALID VALUES: ['Approved - Paid', 'Approved - Processed', 'Failed'].
--   - PriceTypeDescr (NVARCHAR): VALID VALUES: ['Retail Subscription', 'Affiliate', 'Retail'].
--   - CountryCode (NVARCHAR): Country where the order was placed.

-- Table: ttvOrderDetails
-- Description: Contains line-item details for each order.
-- Columns:
--   - OrderId (BIGINT): The ID of the parent order.
--   - ItemId (INT): The ID of the product/item.
--   - ItemCode (NVARCHAR): SKU or code for the item.
--   - ItemDescr (NVARCHAR): Description/Name of the item.
--   - Quantity (DECIMAL): Quantity ordered.
--   - ItemPriceTotal (MONEY): Total price for this line (Price * Qty).
--   - QVTotal (MONEY): Total Qualifying Volume for this line.
--   - CVTotal (MONEY): Total Commissionable Volume for this line.

-- Table: ttvTrees
-- Description: Stores hierarchical structures (Enroller, Binary, Matrix, Unilevel).
-- Columns:
--   - TreeType (INT): The type of tree.
--   - TreeTypeDescr (NVARCHAR): VALID VALUES: ['Enroller']. (Assumed Binary/Matrix exist if strictly requested).
--   - CustomerId (BIGINT): The customer ID.
--   - ParentId (BIGINT): The immediate parent ID in this specific tree.
--   - NestedLevel (INT): Depth level (0 = Root, 1 = First Level, etc.).
--   - PlacementId (INT): Leg position (e.g., 1 = Left, 2 = Right in Binary).
--   - LeftId (BIGINT): Nested Set Left boundary (Use for downline queries).
--   - RightId (BIGINT): Nested Set Right boundary (Use for downline queries).
"""

def generate_sql_query(user_question):
    """
    Generates a SQL query from a natural language question based on the defined schema.
    """
    
    # Check for OpenAI Config
    try:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-35-turbo")
        
        # Note: You might need to add AZURE_OPENAI_CHAT_DEPLOYMENT to your .env
        # using the existing embedding deployment strictly for embeddings won't work for chat completions
        # if the model doesn't support it.
        
        if not api_key or not endpoint:
            return "Error: OpenAI Environment variables missing."
            
        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-01",
            azure_endpoint=endpoint
        )

        system_prompt = f"""You are a SQL expert. 
Given the following database schema, generate a valid SQL query to answer the user's question.
Do NOT output any markdown, backticks, or explanations. Just the raw SQL query.

Schema:
{DATABASE_SCHEMA}
"""

        response = client.chat.completions.create(
            model=deployment, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error creating SQL: {str(e)}"

if __name__ == "__main__":
    print("--- SQL Generation Prototype ---")
    q = input("Enter a natural language question: ")
    sql = generate_sql_query(q)
    print(f"\nGenerated SQL:\n{sql}")
