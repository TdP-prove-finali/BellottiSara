from database.DAO import DAO

campagne = DAO.getAllCampaigns()

print(len(campagne))
print(campagne[0])
