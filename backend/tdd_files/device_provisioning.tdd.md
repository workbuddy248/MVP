# Test Design Document: Device Provisioning

## Overview
Automate the provisioning of network devices in Cisco Catalyst Centre.

## Test Objective
Add and configure new network devices with proper credentials and settings.

## Prerequisites
- Device discovery must be enabled
- SNMP credentials configured
- Network reachability to devices

## Test Data
- **Device IP**: [device_ip:ip:required] - IP address of the device to provision
- **Device Type**: [device_type:dropdown:required:default=Switch] - Type of network device
- **SNMP Community**: [snmp_community:password:required:default=public] - SNMP community string
- **Enable SSH**: [enable_ssh:boolean:optional:default=true] - Enable SSH access
- **Management VLAN**: [mgmt_vlan:number:optional:default=1] - Management VLAN ID

## Test Steps

### Step 1: Navigate to Device Management
1. Login to Catalyst Centre
2. Go to **Provision > Network Device > Inventory**
3. Click **+ Add Device**

### Step 2: Device Discovery
1. Enter device IP: `{device_ip}`
2. Select device type: `{device_type}`
3. Configure SNMP community: `{snmp_community}`

### Step 3: Device Configuration
1. Set management VLAN: `{mgmt_vlan}`
2. Enable SSH if selected: `{enable_ssh}`
3. Click **Discover** button

### Step 4: Verify Provisioning
1. Check device appears in inventory
2. Verify device status is "Managed"
3. Test device connectivity

## Expected Results
- Device successfully added to inventory
- Device status shows "Managed"
- All configurations applied correctly

## Category
device_management

## Dependencies
- network_hierarchy

## Estimated Duration
1200 seconds
