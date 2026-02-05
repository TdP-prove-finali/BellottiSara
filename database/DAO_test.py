from database.DAO import DAO

campagne = DAO.getAllCampaigns(50000)
users_1 = DAO.getAllUsers("Female" , "25-34", "France", "fashion", None)
users_2 = DAO.getAllUsers("Male" , "25-34", "United States", "fitness", "technology")
#archiKPI = DAO.getAllEdgesWithKPI([1, 3, 4, 7, 8, 9, 10, 12, 13, 14, 18, 19, 21, 22, 23, 26, 27, 28, 29, 34, 37, 42, 44, 48, 49, 50] , ['687d1', '4fbc0', '6eef7', '2a233', '52e2e', 'a49e8', '0863c', '66bba', '8ddb8', '91674', 'ea1ba', 'b7fbc', '01e28', 'be496', '9d842', 'aaaef', '885c1'])

edgesWeight_1 = DAO.getAllEdgesWeight([1, 3, 4, 7, 8, 9, 10, 12, 13, 14, 18, 19, 21, 22, 23, 26, 27, 28, 29, 34, 37, 42, 44, 48, 49, 50], ['2a233', '52e2e', 'a49e8', '66bba', '91674', 'ea1ba', 'b7fbc', '01e28', 'be496', 'aaaef'])
edgesWeight_2 = DAO.getAllEdgesWeight([1, 3, 4, 7, 8, 9, 10, 12, 13, 14, 18, 19, 21, 22, 23, 26, 27, 28, 29, 34, 37, 42, 44, 48, 49, 50], ['099e3', '9ff6f', '116eb', '0429c', 'c61fb', 'db8a2', 'bf967', 'c135e', '063ee', '1177a', '2b7c8', 'a11cb', '91914', '346ba', 'bae96', '551d6', '3ef28', '7ac71', '8971e', '8d184', 'e077a', 'f6ef2', 'ee263', 'f8c7a', '579ac', '555f6', 'e6846', '56f34', '004a5', '15ad4', '435c6', '4c893', '4ee56', '06706', '0058e', '17ce1', '5c221', '5a2cd', 'e030c', '08e08', '63ccd', '147a0', '433b9', '8a5ad', '77938', 'a1b50', '29ae1', 'e0abc', '77aa7', 'd96cc', '8d42e', '1f32f', '8e2d8', '3e7b5', '5dea4', '887cc', '27baa', '0162f', '43428', '4e226', 'e46f7', '84a60', 'f69fb', 'e21d1', '7e587', '0e9cb', '3016e', '8d0db', '71097', '5fe31', 'a46f2', 'd15db', '8acac', '58f9b', '48aaf', 'dd7ad', '547c2', '11556', 'd9381', 'cb97c', '8ea62', '473e3', 'c7c57', '5bbca', '81ed3', 'ab1ec', '0ab8b', '81168', 'e3205', '5c86e', 'bae2c', '3388a', '01440', '2ef58', '008c5', 'a1d14', 'fd56c', 'a810c', '565a6', 'e1a2e', 'beb84', '37820', '02e21', 'a1c5a', '0b673', 'e319b', '2b870', 'a6804', '6f233', 'd89ba', 'f822b', '1f381', 'bbb51', 'f562b', '4325f', 'ebb43', '2adea', '5d93c', '01029', 'afc3d', '2abc2', '297bb', '67f2d', 'ef248', '8dc0e', '55830', 'a154d', '0e9ed', 'aaa43', '2633a', 'ee0a7', 'd2744', '4f986', '0a531', '29134', 'df9d9', 'b97d1', '63da8', '50b82', '58a5e', '60812', 'f321d', 'caa25', '80ff3', '6f7ed', '3968b', 'eb535', '714bc', 'f82d9', '22062', '935da', '01816', '84367', 'a2bc2', '5a216', '5803f', 'a4221', 'eee97', 'f707b', 'adbdf', '85bd6', '99da6', 'ecc13', 'ebfe3', 'e873f', '7a9e9', 'f29cf', '6e1a6', '75565', '637d9', '12b06', '1ab1d', '8a9eb', 'ca901', 'f234b', '54c86', 'e7d43', 'ee956', '05a92', 'baebc', 'ba58e', '0b8c2', '741f4', '6d917'])

print(len(campagne))
print(campagne)
print(len(users_1))
print(users_1)
#print(len(archiKPI))
print(len(edgesWeight_1))
print(edgesWeight_1[:5])
print(len(edgesWeight_2))
print(edgesWeight_2[:5])
