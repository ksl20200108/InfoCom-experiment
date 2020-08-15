print("version: '2'")
print('\nservices:')

for i in range(1, 115):
    print('  couchdb' + str(i) + ':')
    print('    image: hyperledger/fabric-couchdb')
    print('    container_name: c' + str(i))
    print('    ports:')
    print('      - ' + str(5983 + i) + ':5984\n')


print('\n')
print('networks: ')
print('  default:')
print('    external: ')
print('      name: genesis  # docker network create --subnet=192.168.118.0/24 genesis')
