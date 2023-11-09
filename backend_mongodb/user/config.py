from pymongo import MongoClient

# MongoDB connection settings
client = MongoClient("mongodb://localhost:27017/")

# Select the database 
db1 = client["mydatabase_monolith"]

# Create a reference to the "user" collection 
user_collection1 = db1["user_monolith"]


# Select the database 
db2 = client["mydatabase_post_monolith"]

# Create a reference to the "post" collection 
user_collection2 = db2["post_monolith"]


# Select the database 
db3 = client["mydatabase_notification_monolith"]

# Create a reference to the "user" collection 
user_collection3 = db3["notification_monolith"]



