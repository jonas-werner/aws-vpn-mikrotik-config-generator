
###################################################################################################################
#                                      __       __  ____ __              __  _ __   ______            _____      
#    ____ ____  ____  ___  _________ _/ /____  /  |/  (_) /___________  / /_(_) /__/ ____/___  ____  / __(_)___ _
#   / __ `/ _ \/ __ \/ _ \/ ___/ __ `/ __/ _ \/ /|_/ / / //_/ ___/ __ \/ __/ / //_/ /   / __ \/ __ \/ /_/ / __ `/
#  / /_/ /  __/ / / /  __/ /  / /_/ / /_/  __/ /  / / / ,< / /  / /_/ / /_/ / ,< / /___/ /_/ / / / / __/ / /_/ / 
#  \__, /\___/_/ /_/\___/_/   \__,_/\__/\___/_/  /_/_/_/|_/_/   \____/\__/_/_/|_|\____/\____/_/ /_/_/ /_/\__, /  
# /____/                                                                                                /____/   
###################################################################################################################
# Author: Jonas Werner
# Version: 1
###################################################################################################################

import xmltodict
import requests
import boto3

# Creating the boto3 session to pull VPN info from AWS
session = boto3.Session(profile_name='default')
ec2_client = session.client('ec2')

configFull        = ec2_client.describe_vpn_connections()
# This is the internal address of your Mikrotik router, provided it is behind an ISP modem / router
localAddress    = "192.168.0.180"
# The CIDR of your AWS VPC / subnet you want to link with
vpcCidr         = "172.30.0.0/16"
url             = "http://icanhazip.com/"
headers         = {'content-type': 'application/json'}
publicIpAddress = requests.post(url, headers=headers, verify=False)


def main():

    cgwConfigXml = configFull["VpnConnections"][0]["CustomerGatewayConfiguration"]
    cgwConfigDict = xmltodict.parse(cgwConfigXml)

    # Creating some shorthand
    t0 = cgwConfigDict["vpn_connection"]["ipsec_tunnel"][0]
    t1 = cgwConfigDict["vpn_connection"]["ipsec_tunnel"][1]

    # Generate Mikrotik config
    ######################################
    # Tunnel 0 IP address
    t0ip = t0["customer_gateway"]["tunnel_inside_address"]["ip_address"]
    t0cidr = t0["customer_gateway"]["tunnel_inside_address"]["network_cidr"]
    print("ip address add address=%s/%s interface=sfp-sfpplus1" % (t0ip, t0cidr))

    # Tunnel 1 IP address
    t1ip = t1["customer_gateway"]["tunnel_inside_address"]["ip_address"]
    t1cidr = t1["customer_gateway"]["tunnel_inside_address"]["network_cidr"]
    print("ip address add address=%s/%s interface=sfp-sfpplus1" % (t1ip, t1cidr))

    # IPsec tunnels
    t0ipsecPeer = t0["vpn_gateway"]["tunnel_outside_address"]["ip_address"]
    print("ip ipsec peer add address=%s local-address=%s name=AWS-VPN-Peer-0" % (t0ipsecPeer, localAddress))
    t1ipsecPeer = t1["vpn_gateway"]["tunnel_outside_address"]["ip_address"]
    print("ip ipsec peer add address=%s local-address=%s name=AWS-VPN-Peer-1" % (t1ipsecPeer, localAddress))

    # IPsec secrets
    t0ipsecSecret = t0["ike"]["pre_shared_key"]
    print("ip ipsec identity add peer=AWS-VPN-Peer-0 secret=%s" % t0ipsecSecret)
    t1ipsecSecret = t1["ike"]["pre_shared_key"]
    print("ip ipsec identity add peer=AWS-VPN-Peer-1 secret=%s" % t1ipsecSecret)

    # IPsec profile settings
    if(t0["ipsec"]["perfect_forward_secrecy"] == "group2"): 
        ipsecProfDh = "modp1024"
    elif(t0["ipsec"]["perfect_forward_secrecy"] == "group5"): 
        ipsecProfDh = "modp1536"
    elif(t0["ipsec"]["perfect_forward_secrecy"] == "group14"): 
        ipsecProfDh = "modp2048"
    ipsecProfDpdInt     = t0["ipsec"]["dead_peer_detection"]["interval"]
    ipsecProfDpdRet     = t0["ipsec"]["dead_peer_detection"]["retries"]
    ipsecPropEnc        = t0["ipsec"]["encryption_protocol"]
    ipsecProfEnc        = ipsecPropEnc[0:7]
    ipsecProfLifetime   = int(int(t0["ike"]["lifetime"])/60/60)

    print("ip ipsec profile set [ find default=yes ] dh-group=%s dpd-interval=%ss dpd-maximum-failures=%s enc-algorithm=%s lifetime=%sh" % (ipsecProfDh, ipsecProfDpdInt, ipsecProfDpdRet, ipsecProfEnc, ipsecProfLifetime))

    # IPsec property settings
    ipsecPropLifetime   = int(int(t0["ipsec"]["lifetime"])/60/60)
    print("ip ipsec proposal set [ find default=yes ] enc-algorithm=%s lifetime=%sh" % (ipsecPropEnc, ipsecPropLifetime))

    # BGP settings
    bgpCgwAsn = t0["customer_gateway"]["bgp"]["asn"]
    print("routing bgp instance set default as=%s redistribute-connected=yes redistribute-static=yes router-id=%s" % (bgpCgwAsn, (publicIpAddress.text).strip()))

    t0bgpHoldTime = t0["vpn_gateway"]["bgp"]["hold_time"]
    t0bgpAliveTime = ipsecProfDpdInt
    t0bgpRemoteAddress = t0["vpn_gateway"]["tunnel_inside_address"]["ip_address"]
    t0bgpRemoteAs = t0["vpn_gateway"]["bgp"]["asn"]
    print("routing bgp peer add hold-time=%ss keepalive-time=%ss name=AWS-VPN-Peer-0 remote-address=%s remote-as=%s" % (t0bgpHoldTime, t0bgpAliveTime, t0bgpRemoteAddress, t0bgpRemoteAs))

    t1bgpRemoteAddress = t1["vpn_gateway"]["tunnel_inside_address"]["ip_address"]
    print("routing bgp peer add hold-time=%ss keepalive-time=%ss name=AWS-VPN-Peer-1 remote-address=%s remote-as=%s" % (t0bgpHoldTime, t0bgpAliveTime, t1bgpRemoteAddress, t0bgpRemoteAs))

    # Networks to advertise to AWS over BGP (change these to match your on-prem networks which you want to advertise to your AWS VPC)
    print("routing bgp network add network=192.168.0.0/24")
    print("routing bgp network add network=10.42.0.0/24")

    # Allowing tunnel and AWS VPC CIDRs through firewall
    print("ip firewall nat add action=accept chain=srcnat dst-address=169.254.0.0/16")
    print("ip firewall nat add action=accept chain=srcnat dst-address=%s" % vpcCidr)


    # Create IPsec policies
    t0ipsecCgwIp = t0["customer_gateway"]["tunnel_inside_address"]["ip_address"]
    t0ipsecVgwIp = t0["vpn_gateway"]["tunnel_inside_address"]["ip_address"]
    t1ipsecCgwIp = t1["customer_gateway"]["tunnel_inside_address"]["ip_address"]
    t1ipsecVgwIp = t1["vpn_gateway"]["tunnel_inside_address"]["ip_address"]

    print("ip ipsec policy add dst-address=%s src-address=%s proposal=default peer=AWS-VPN-Peer-0 tunnel=yes" % (t0ipsecVgwIp, t0ipsecCgwIp))
    print("ip ipsec policy add dst-address=%s src-address=%s proposal=default peer=AWS-VPN-Peer-1 tunnel=yes" % (t1ipsecVgwIp, t1ipsecCgwIp))

    # Disable one of the tunnels since Mikotik doesn't support routing over both
    print("ip ipsec policy disable [find peer=\"AWS-VPN-Peer-1\"]")
    # Add routing to the AWS VPC CIDR
    print("ip ipsec policy add dst-address=%s src-address=0.0.0.0/0 proposal=default peer=AWS-VPN-Peer-0 tunnel=yes" % (vpcCidr))


if __name__ == "__main__":
    main()

