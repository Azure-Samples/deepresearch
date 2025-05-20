targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param name string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

param acaExists bool = false

@minLength(1)
@description('Location for the Azure AI resource')
// https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-serverless-availability#deepseek-models-from-microsoft
@allowed([
  'eastus'
  'eastus2'
  'northcentralus'
  'southcentralus'
  'westus'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param aiServicesResourceLocation string
param disableKeyBasedAuth bool = false

// Parameters for the specific Azure AI deployment:
param aiServicesDeploymentName string = 'DeepSeek-R1'

@description('Service Management Reference for the Entra app registration')
param serviceManagementReference string = ''

var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${name}-rg'
  location: location
  tags: tags
}

var prefix = '${name}-${resourceToken}'

var aiServicesNameAndSubdomain = '${resourceToken}-aiservices'
module aiServices 'br/public:avm/res/cognitive-services/account:0.7.2' = {
  name: 'deepseek'
  scope: resourceGroup
  params: {
    name: aiServicesNameAndSubdomain
    location: aiServicesResourceLocation
    tags: tags
    kind: 'AIServices'
    customSubDomainName: aiServicesNameAndSubdomain
    sku: 'S0'
    publicNetworkAccess: 'Enabled'
    deployments: [
      {
        name: aiServicesDeploymentName
        model: {
          format: 'DeepSeek'
          name: 'DeepSeek-R1'
          version: '1'
        }
        sku: {
          name: 'GlobalStandard'
          capacity: 1
        }
      }
    ]
    disableLocalAuth: disableKeyBasedAuth
    roleAssignments: [
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'Cognitive Services User'
      }
    ]
  }
}

module logAnalyticsWorkspace 'core/monitor/loganalytics.bicep' = {
  name: 'loganalytics'
  scope: resourceGroup
  params: {
    name: '${prefix}-loganalytics'
    location: location
    tags: tags
  }
}

// Container apps host (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    location: location
    tags: tags
    containerAppsEnvironmentName: '${prefix}-containerapps-env'
    containerRegistryName: '${replace(prefix, '-', '')}registry'
    logAnalyticsWorkspaceName: logAnalyticsWorkspace.outputs.name
  }
}

// Container app frontend
module aca 'aca.bicep' = {
  name: 'aca'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix,19)}-ca', '--', '-')
    location: location
    tags: tags
    identityName: '${prefix}-id-aca'
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    aiServicesDeploymentName: aiServicesDeploymentName
    aiServicesEndpoint: 'https://${aiServices.outputs.name}.services.ai.azure.com/models'
    exists: acaExists
  }
}

var issuer = '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
module registration 'appregistration.bicep' = {
  name: 'reg'
  scope: resourceGroup
  params: {
    clientAppName: '${prefix}-entra-client-app'
    clientAppDisplayName: 'DeepSeek Entra Client App'
    webAppEndpoint: aca.outputs.uri
    webAppIdentityId: aca.outputs.identityPrincipalId
    issuer: issuer
    serviceManagementReference: serviceManagementReference
  }
}

module appupdate 'appupdate.bicep' = {
  name: 'appupdate'
  scope: resourceGroup
  params: {
    containerAppName: aca.outputs.name
    clientId: registration.outputs.clientAppId
    openIdIssuer: issuer
    includeTokenStore: false
  }
}

module aiServicesRoleBackend 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'aiservices-role-backend'
  params: {
    principalId: aca.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId

output AZURE_DEEPSEEK_DEPLOYMENT string = aiServicesDeploymentName
output AZURE_INFERENCE_ENDPOINT string = 'https://${aiServices.outputs.name}.services.ai.azure.com/models'
output AI_SERVICES_NAME string = aiServicesNameAndSubdomain


output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.identityPrincipalId
output SERVICE_ACA_NAME string = aca.outputs.name
output SERVICE_ACA_URI string = aca.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.imageName

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName
