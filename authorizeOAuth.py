#!/usr/bin/env python3

################### README ###################
# Requirements: python3, sfdx, open
#   Built for MacOS, not cross-OS-compatible
# Developer: Robert Nordman
# Email: rnordman@asu.edu
# Slack: @rnordman
# Date: November 9, 2022
# Description:
#   After refreshing a sandbox the Mule API 
#   user in that sandbox needs to re-authorize
#   the connected app to act on its behalf -
#   this script steps through that process,
#   automating what could easily be automated
##############################################

# Values that might change depending on who is running this and in what context
yourUsername = 'rnordman@asu.edu.dev' # The user the REST calls will act on behalf of
sfUrl = 'https://asu--dev.my.salesforce.com' # which sandbox URL
apiUsername = 'mulesoft@asu.edu.dev'  # username of the api user
apiUserNewEmail = 'rnordman@asu.edu' # we will change the api user's email to this so that you can receive MFA codes via email

# Connected app to authorize the api user against (this reference the app key for the connected app in the AUTH sandbox)
connectedAppKey = '3MVG9E8TNx7FN9y5IIxhV_Zl8NYeZyybOSRdJJqMbdh.IWEMocqHGBsLFcHlrC4cpnxc3SeU7i1kybJjJpPmK'

# Rarely need to change
sfVersion = 'v56.0'
permissionSetName = 'API_Only_User'
browserCommand = 'open'

# Global vars that will be handled by code
apiUserId = None
permissionSetId = None
hd = {}
hd['Content-Type'] = 'application/json'

def main():
    global sfUrl, apiUsername, apiUserId, permissionSetName, permissionSetId
    
    # We need to login to SF as ourself (a sysadmin) so we can get the bearer token to use the REST API
    print("...Using sfdx to authorize with Salesforce as your user")
    loginToSalesforceAsYourself()
    print(f'   Authenticated using sfdx in {sfUrl}')
    
    # We will get the bearer token sfdx is using - and use that for our REST API calls
    print("...Getting bearer token")
    setBearerToken()
    print("   Bearer token obtained")
    
    # Query for the permission set and user ids
    print(f"...Getting user id for {apiUsername}")
    setUserId()
    print(f"   User with username {apiUsername} has id {apiUserId}")
    print(f"...Getting permission set id for {permissionSetName}")
    setPermissionSetId()
    print(f"   Permission set with name {permissionSetName} has id {permissionSetId}")
    
    # Remove the API User Only Perm Set from the api user
    print("...Removing permission set assignment")
    removePermSet()
    print(f'   {permissionSetName} permission set has been removed from {apiUsername}')

    # Need to login as the api user to authorize connected app on their behalf
    print("...Changing api user's email address")
    updateUserEmail()
    print("   Changed api user's email adress.")
    input("Press enter to continue after approving email change via sent email...")

    # Now logout the user so that we can later login as the api user
    print("...Logging you out of your user - so that you can login as the api user")
    logoutInBrowser()
    input("   Press enter to continue once logged out...")
    
    # Next force the user to go through the in browser flow to authorize the connected app
    print("...Opening browser to authorize connected app as api user")
    authorizeInBrowser()
    input('   Press enter to continue after completing in browser flow as the API user...')
    
    # Finally re-add the API User Only Perm Set from the api user
    print("...Readding permission set")
    addPermSet()
    print(f'   {permissionSetName} permission set has been added to {apiUsername}')

    # Logout of API user in browser
    print("...Logging out of the api user account in browser")
    logoutInBrowser()
    print("   Once you've logged out in browser - this process is complete")

# Ask the user to login in SF in browser
def loginToSalesforceAsYourself():
    global sfUrl
    subprocess.run(f"sfdx force:auth:web:login -r {sfUrl}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
# Set the bearer token in the header global var
def setBearerToken():
    global hd
    bearerToken = getToken()
    hd['Authorization'] = f'Bearer {bearerToken}'
# Use sfdx to get the bearer token
def getToken():
    global yourUsername
    cmdResult = subprocess.run(f"sfdx force:org:display --json --targetusername {yourUsername}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=20).stdout
    cmdResultStr = str(cmdResult, "latin-1")
    return json.loads(cmdResultStr)['result']['accessToken']

# Set the user id global var
def setUserId():
    global apiUserId
    apiUserId = getUserId()
# Perform SOQL query to get the user's id
def getUserId():
    global sfUrl, sfVersion, apiUsername, hd
    dt = {}
    x = requests.get(f"{sfUrl}/services/data/{sfVersion}/query/?q=SELECT+Id+FROM+User+WHERE+Username+=+'{apiUsername}'", headers=hd, data=dt, verify=True)
    return json.loads(x.text)['records'][0]['Id']

# Set the permission set id global var
def setPermissionSetId():
    global permissionSetId
    permissionSetId = getPermissionSetId()
# Perform SOQL query to get the permission set's id
def getPermissionSetId():
    global sfUrl, sfVersion, permissionSetName, hd
    dt = {}
    x = requests.get(f"{sfUrl}/services/data/{sfVersion}/query/?q=SELECT+Id+FROM+PermissionSet+WHERE+Name+=+'{permissionSetName}'", headers=hd, data=dt, verify=True)
    return json.loads(x.text)['records'][0]['Id']

# Remove the permission set from the user
def removePermSet():
    global sfUrl, sfVersion, permissionSetName, apiUserId, hd
    dt = {}
    x = requests.get(f"{sfUrl}/services/data/{sfVersion}/query/?q=SELECT+Id+FROM+PermissionSetAssignment+WHERE+PermissionSetId+=+'{permissionSetId}'+AND+AssigneeId+=+'{apiUserId}'", headers=hd, data=dt, verify=True)
    if len(json.loads(x.text)['records']) > 0: # only need to delete if the user has the permission set assigned
        permissionSetAssignmentId = json.loads(x.text)['records'][0]['Id']
        x = requests.delete(f'{sfUrl}/services/data/{sfVersion}/sobjects/PermissionSetAssignment/{permissionSetAssignmentId}', headers=hd, data=dt, verify=True)

# Update the email of the API user to us - that way we can receive the 2FA codes
def updateUserEmail():
    global sfUrl, sfVersion, permissionSetName, apiUserId, apiUserNewEmail, hd
    dt = {
        "Email": apiUserNewEmail
    }
    x = requests.patch(f'{sfUrl}/services/data/{sfVersion}/sobjects/User/{apiUserId}/', headers=hd, data=json.dumps(dt), verify=True)

# Add the permission set to the user
def addPermSet():
    global sfUrl, sfVersion, permissionSetName, apiUserId, hd
    dt = {
        "AssigneeId": apiUserId,
        "PermissionSetId": permissionSetId
    }
    x = requests.post(f'{sfUrl}/services/data/{sfVersion}/sobjects/PermissionSetAssignment/', headers=hd, data=json.dumps(dt), verify=True)

# Open the browser to log the user out
def logoutInBrowser():
    global browserCommand, sfUrl
    url = f'{sfUrl}/secur/logout.jsp'
    subprocess.run(f"{browserCommand} \"{url}\"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

# Open the browser so user authorize the connected app
def authorizeInBrowser():
    global browserCommand, sfUrl, connectedAppKey
    randomState = randomString(10)
    randomNonce = randomString(11)
    url = f'{sfUrl}/services/oauth2/authorize?client_id={connectedAppKey}&redirect_uri=https%3A%2F%2Foauthdebugger.com%2Fdebug&scope=api%20refresh_token%20offline_access%20openid&response_type=code&response_mode=query&state={randomState}&nonce={randomNonce}'
    subprocess.run(f"{browserCommand} \"{url}\"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).stdout

# generate a random string for length l (Not a good random generator - but good enough for this)
def randomString(l):
    startStr = base64.b64encode(str(random.random()).encode('ascii')).decode('ascii').replace("=","_").replace("+",".")
    while len(startStr) != l:
        if len(startStr) < l:
            startStr += base64.b64encode(str(random.random()).encode('ascii')).decode('ascii').replace("=","_").replace("+",".")
        elif len(startStr) > l:
            startStr = startStr[:l]
    return startStr

# Import needed classes
import requests
import subprocess
import json
import random
import base64
# and run!
main()