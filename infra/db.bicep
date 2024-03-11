param accountName string
param location string = resourceGroup().location
param tags object = {}

param databaseName string = 'db_conversation_history'
param conversationsCollectionName string = 'conversations'
param userSettingsCollectionName string = 'user_settings' 
param principalIds array = []

param containers array = [
  {
    name: conversationsCollectionName
    id: conversationsCollectionName
    partitionKey: '/userId'
  }
  {
    name: userSettingsCollectionName
    id: userSettingsCollectionName
    partitionKey: '/userId'
  }
]

module cosmos 'core/database/cosmos/sql/cosmos-sql-db.bicep' = {
  name: 'cosmos-sql'
  params: {
    accountName: accountName
    databaseName: databaseName
    location: location
    containers: containers
    tags: tags
    principalIds: principalIds
  }
}


output databaseName string = cosmos.outputs.databaseName
output conversationsContainerName string = containers[0].name
output usersettingsContainerName string = containers[1].name
output accountName string = cosmos.outputs.accountName
output endpoint string = cosmos.outputs.endpoint
