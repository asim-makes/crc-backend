// main.bicep


// Parameters
@description('Azure region to deploy resources into.')
param location string = resourceGroup().location


// Azure Function params
@description('Name for the Azure Functions hosting plan.')
param hostingPlanName string = 'crc-hosting-plan'
@description('Name for the Azure Functions App.')
param functionAppName string = 'crc-func-visitor'
@description('Name for the storage account required by the function app.')
param storageAccountName string = 'crcresumestorage'
@description('Name for the Application Insights resource.')
param appInsightName string = 'visitor-func-app-insight'



// CosmosDB parameters
@description('Name for the Cosmos DB Account')
param cosmosAccountName string = 'visitor-counter-table'
@allowed([
  'Eventual'
  'ConsistentPrefix'
  'Session'
  'BoundedStaleness'
  'Strong'
])
param defaultConsistencyLevel string = 'Session'
@description('The name for the Cosmos DB table.')
param cosmosTableName string = 'visitor-counter'


// Resources


// Resource 1: Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}


// Resource 2: Application Insights
resource applicationInsight 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}


// Resource 3: Consumption Hosting Plan for the function app
resource hostingPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: hostingPlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}



// Resource 4: Create the CosmosDB Account
resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2022-05-15' = {
  name: toLower(cosmosAccountName)
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    capabilities: [
      {
        name: 'EnableTable'
      }
    ]
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: defaultConsistencyLevel
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
  }
}


// Create the CosmosDB Table
resource cosmosTable 'Microsoft.DocumentDB/databaseAccounts/tables@2022-05-15' = {
  parent: cosmosDb
  name: cosmosTableName
  properties: {
    resource: {
      id: cosmosTableName
    }
  }
}



// Deploy the function app
resource functionApp 'Microsoft.Web/sites@2021-02-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  properties: {
    reserved: true
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'python|3.11'
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsight.properties.ConnectionString
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        } 
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'CosmosDbConnection'
          value: 'DefaultEndpointsProtocol=https;AccountName=${cosmosDb.name};AccountKey=${cosmosDb.listKeys().primaryMasterKey};TableEndpoint=https://${cosmosDb.name}.table.cosmos.azure.com:443/'
        }
        {
          name: 'CosmosDbTableName'
          value: cosmosTable.name
        }
      ]
    }
  }
}
