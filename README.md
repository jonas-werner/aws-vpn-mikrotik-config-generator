# Summary
This script uses Python and boto3 to read in an AWS VPN configuration directly from AWS and then generates the commands to bring up the ipsec tunnels and enable BGP routing for a Mikrotik router - all in a few seconds. 

# Audience / when to use
If you have a Mikrotik router in your home lab or on-prem DC and want to quickly be able to bring up a VPN tunnel to AWS - this will be a quick way to generate the commands for it. The reason for creating the script was that I have a home lab which needs connectivity to AWS every now and then but I didn't want to pay for the VPN connection while I'm not using it. Manually establishing the IPsec peers, BGP routing, etc. every time was a lot of work and a waste of time if doing it frequently. 

# How to use
Create the CGW, VGW and S2S VPN connection in AWS first. If uncertain how to do this - please refer to this blog post: https://jonamiki.com/2022/05/04/mikrotik-vpn-to-aws-vpc/
It will use your ~/.aws/credentials to gather the info required to generate the Mikrotik commands.Make sure you have AWS CLI access with permissions to read VPC VPN configurations before executing the script. At least use credentials holding the "AmazonVPCReadOnlyAccess" permission policy. 

# What's not included
You still need to add the return route to your on-prem environment by modifying the routing table for the VPC / subnet you have your resources deployed into. For example, set a route for your onprem 192.168.0.0/24 subnet to go via your AWS VGW (or Virtual Private Gateway). Also, add a route on the Mikrotik for your AWS network so it knows to route traffic there. For example: "[admin@CRS309] > ip ipsec policy add dst-address=172.30.0.0/16 src-address=0.0.0.0/0 proposal=default peer=AWS-VPN-Peer-0 tunnel=yes" to have traffic bound for AWS to go over tunnel 0. Finally, disable one of the VPN tunnels. The Mikrotik doesn't support routing over two tunnels currently. Of course, disable the tunnel NOT used to route to your AWS VPC - in this example that would be tunnel 1. For example: "[admin@CRS309] > ip ipsec policy disable 2" where "2" denotes tunnel 1 (counting start from 0). Again, please refer to this blog post for details: https://jonamiki.com/2022/05/04/mikrotik-vpn-to-aws-vpc/
