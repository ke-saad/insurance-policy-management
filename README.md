# Flask Policy Management System

This project is a Flask-based web application for managing insurance policies. It provides endpoints to interact with a SQL database and a MongoDB collection, allowing users to retrieve, add, update, and delete policy information. The application also supports file upload for data input.

## Features

- **SQL Database Interaction:** Interact with a SQL database to manage policy information including policy number, holder name, coverage amount, and premium amount.

- **MongoDB Integration:** Access and manage additional policy information in a MongoDB collection, including claims info and policy documents.

- **Combined Data Display:** Retrieve and display combined policy information from both SQL and MongoDB sources.

- **File Upload:** Upload CSV or XLSX files to add multiple policies at once.

## Getting Started

1. Install the required packages by running:

   ```bash
   pip install -r requirements.txt

2. API Endpoints:

   GET /get/main infos: Retrieve policy information from the SQL database.

   GET /get/secondary infos: Retrieve policy information from the MongoDB collection.

   GET /get/exhaustive list: Retrieve combined policy information from both SQL and MongoDB sources.

   POST /post: Add a new policy to the database. Supports adding policy information to both SQL and MongoDB.

   PUT /put/{policy_id}: Update an existing policy by policy ID. Supports updating policy information in both SQL and MongoDB.

   DELETE /delete/{policy_id}: Delete a policy by policy ID. Removes the policy from both SQL and MongoDB.

   POST /upload: Upload a CSV or XLSX file to add multiple policies at once.

3.Usage

   You can use tools like Postman or any API testing tool to interact with the API endpoints. Remember to include the necessary request data in the correct format.
   Contributing:

   Contributions are welcome! If you find any issues or have suggestions for improvements, feel free to create a pull request or open an issue.

   License
   This project is licensed under the MIT License.

   This project was developed by ke-saad.