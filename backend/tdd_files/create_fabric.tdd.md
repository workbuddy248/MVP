# Test Design Document: Create Network Fabric

## Overview
This TDD describes the automated workflow for creating a new Software Defined Access (SDA) fabric in Cisco Catalyst Centre.

## Test Objective
Create a new network fabric with proper BGP configuration, site hierarchy assignment, and L3 handoff settings.

## Prerequisites
- Network hierarchy must exist in the system
- User must have administrative privileges
- Catalyst Centre must be accessible

## Test Data
- **Fabric Name**: [fabric_name:text:required] - Unique identifier for the fabric
- **BGP ASN**: [bgp_asn:number:required:default=65001] - BGP Autonomous System Number
- **Site Hierarchy**: [site_hierarchy:dropdown:required] - Network site location
- **Enable L3 Handoff**: [enable_l3_handoff:boolean:optional:default=true] - Layer 3 handoff configuration
- **Transit Type**: [transit_type:dropdown:required:default=IP_BASED_TRANSIT] - Type of transit network

## Test Steps

### Step 1: Navigate to Fabric Management
1. Login to Cisco Catalyst Centre
2. Navigate to **Design > Network Settings > Network**
3. Click on **Fabric** tab

### Step 2: Create New Fabric
1. Click **+ Add Fabric** button
2. Enter fabric name: `{fabric_name}`
3. Select site hierarchy: `{site_hierarchy}`
4. Configure BGP ASN: `{bgp_asn}`

### Step 3: Configure Advanced Settings
1. Set transit type to: `{transit_type}`
2. Enable/disable L3 handoff: `{enable_l3_handoff}`
3. Click **Save** button

### Step 4: Verify Fabric Creation
1. Verify fabric appears in fabric list
2. Check fabric status is "Active"
3. Validate configuration matches input parameters

## Expected Results
- Fabric is successfully created with specified configuration
- Fabric status shows as "Active"
- All configuration parameters are correctly applied

## Category
fabric

## Dependencies
- network_hierarchy

## Estimated Duration
900 seconds
