Test Cases (Write Tests First)
test_get_fabric_workflow
Given: User with valid credentials and access to Catalyst Center
When: User logs in successfully to the system
Then: The system should display "Welcome to Catalyst Centre!" text on home page
When: User clicks on the hamburger menu on the top extreme left
Then: The menu should expand showing navigation options
When: User clicks on Provision option in the menu
And: User clicks on Fabric Sites under SD-Access
Then: The system should navigate to dna/provision/evpn/fabric-sites page
When: User changes the view from overview to table view by clicking the dnx switch div
Then: The system should display table view with "Fabric Site" column
When: User clicks on fabric entry matching the user name in the table
Then: The system should navigate to the fabric details page
When: User clicks on Settings option
Then: The system should load the settings page completely
Then: The system should take a screenshot and mark test as successful
