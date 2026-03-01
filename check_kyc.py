from pymongo import MongoClient

# 🔒 Use your updated Atlas connection string
MONGO_URI = "mongodb+srv://petercokey96_db_user:BURCwBViMbuKEuRh@cluster0.7fpmm0p.mongodb.net/househaunt?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)

db = client["househaunt"]

doc = db.kyc.find_one()

print("First KYC document:")
print(doc)

client.close()