# Database Module

#### Test

This module contains functions to populate the database with fake data.

#### Utils

This contains helper SQLs not required for containers. Currently, this module contains the migration script from the old
database and versioning activation.

#### Schemas

This contains all schemas used for the application creation. These are executed in alphabetical order on container
creation. __The order is really important__.