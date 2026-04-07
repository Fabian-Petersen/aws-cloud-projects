# Problem Statement and Solution Overview

## Problem Statement

In our current system, user data is managed by **Amazon Cognito**, which serves as the authentication and identity provider. While Cognito stores essential user attributes (such as email, name, and status), it has several limitations for administrative and frontend use:

1. **Nested Data Structure**  
   Cognito returns user attributes in a nested object (e.g., `attributes.email`, `attributes.name`), which complicates frontend data handling and table rendering.

2. **No Built-in Group Aggregation**  
   Cognito stores group memberships separately from user attributes. Admin APIs like `ListUsers` or `AdminGetUser` do **not include groups**, making it impossible to efficiently display users along with their roles or permissions in a dashboard.

3. **Frontend Scalability Issues**  
   To fetch group data for multiple users, the frontend would have to make **one API call per user**, creating an N+1 problem that results in:
   - Poor performance for large user lists
   - Slow user interface updates
   - Higher API costs and network overhead

4. **Limited Flexibility**  
   Additional user metadata (such as location, internal roles, or system-specific flags) cannot be stored in Cognito without using custom attributes, which is not ideal for dynamic or frequently updated data.

---

## Solution: DynamoDB User Table with Lambda Integration

To address these issues, a **dedicated DynamoDB table** called `users` is used to store enriched user data, synchronized with Cognito via Lambda functions. This architecture includes:

### DynamoDB Table

- **Table Name:** `users`
- **Primary Key:** `id` (Cognito sub)
- **Fields:**
  - `id` (PK)
  - `email`
  - `name`
  - `family_name`
  - `username`
  - `status`
  - `groups` (array)
  - `location`
  - `createdAt`
  - `updatedAt`

---

### Lambda Functions

1. **`postUserTrigger`**
   - Trigger: Cognito **PostConfirmation**
   - Purpose: Add newly created Cognito users into the DynamoDB table
   - Actions:
     - Extract user attributes from Cognito event
     - Insert user record into `users` table
     - Initialize `groups` and `location` fields

2. **`updateUserById`**
   - Trigger: Admin API call (via API Gateway)
   - Purpose: Update user metadata or group assignments in the DynamoDB table
   - Actions:
     - Update specified fields (name, email, groups, location, etc.)
     - Update `updatedAt` timestamp

3. **`deleteUserById`**
   - Trigger: Admin API call (via API Gateway)
   - Purpose: Delete user from the DynamoDB table when removed from Cognito
   - Actions:
     - Delete record by `id` (Cognito sub)

4. **`getUserList`**
   - Trigger: Admin API call (via API Gateway)
   - Purpose: Fetch all users from the DynamoDB table for frontend consumption
   - Actions:
     - Query all items in the `users` table
     - Return enriched data including groups, location, and flattened attributes

---

## Benefits of This Architecture

1. **Flattened and Consistent Data Structure**
   - Frontend can access attributes directly without mapping nested objects.

2. **Groups and Roles Included**
   - Stored as arrays in DynamoDB, avoiding per-user calls to Cognito.

3. **Scalable for Large User Lists**
   - Frontend fetches full dataset in **one request**.

4. **Extensible and Customizable**
   - Add fields like `location`, internal roles, or flags without touching Cognito.

5. **Reliable and Event-Driven Sync**
   - `postUserTrigger` ensures new users are immediately added.
   - `updateUserById` and `deleteUserById` keep the table consistent with Cognito.
   - `getUserList` serves as the fast, frontend-ready read model.

---

### Summary

By integrating Cognito with a **DynamoDB `users` table** and Lambda functions:

- Admin dashboards can query **fully enriched user data** in a single request
- Frontend complexity is reduced
- System scales efficiently without N+1 API calls
- DynamoDB acts as the **read model**, while Cognito remains the **source of truth for authentication and identity**
