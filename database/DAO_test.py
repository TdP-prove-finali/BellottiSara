from database.DAO import DAO

campagne = DAO.getAllCampaigns(50000)
users = DAO.getAllUsers("Female" , "25-34", "France", "fashion", None)

print(len(campagne))
print(campagne)
print(len(users))
print(users)
