#!/usr/bin/env python3
"""
Smart IPAM - IP Address Management Platform
Main application entry point and CLI interface
"""

import click
import asyncio
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import ipaddress
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from smart_ipam.core.ipam_manager import IPAMManager
from smart_ipam.core.subnet_manager import SubnetManager
from smart_ipam.core.discovery_engine import DiscoveryEngine
from smart_ipam.api.gateway_service import create_app
from smart_ipam.utils.logger import setup_logger
from smart_ipam.utils.database import init_database

console = Console()
logger = setup_logger("smart-ipam-cli")


@click.group()
@click.version_option(version="1.0.0", prog_name="Smart IPAM")
def cli():
    """Smart IPAM - Intelligent IP Address Management Platform"""
    pass


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind the server to')
@click.option('--port', default=8080, help='Port to bind the server to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def run_server(host, port, debug):
    """Start the Smart IPAM API gateway service"""
    console.print("🚀 Starting Smart IPAM Gateway Service...", style="bold green")
    
    app = create_app()
    
    console.print(f"📡 Server running on http://{host}:{port}", style="bold blue")
    console.print("📚 API Documentation: http://localhost:8080/api/docs", style="bold cyan")
    console.print("🌐 Web Portal: http://localhost:8080/portal", style="bold cyan")
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        console.print("\n🛑 Server stopped by user", style="bold red")


@cli.command()
def init_database():
    """Initialize the Smart IPAM database"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Initializing Smart IPAM database...", total=None)
        
        try:
            init_database()
            console.print("✅ Database initialized successfully!", style="bold green")
        except Exception as e:
            console.print(f"❌ Database initialization failed: {e}", style="bold red")
            sys.exit(1)


@cli.command()
@click.option('--username', required=True, help='Admin username')
@click.option('--email', required=True, help='Admin email address')
@click.option('--password', prompt=True, hide_input=True, help='Admin password')
def create_admin(username, email, password):
    """Create admin user"""
    try:
        from smart_ipam.utils.auth import create_admin_user
        result = create_admin_user(username, email, password)
        
        if result.get('success'):
            console.print(f"✅ Admin user '{username}' created successfully!", style="bold green")
        else:
            console.print(f"❌ Failed to create admin user: {result.get('error')}", style="bold red")
            sys.exit(1)
    except Exception as e:
        console.print(f"❌ Error creating admin user: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option('--network', required=True, help='Network CIDR (e.g., 192.168.1.0/24)')
@click.option('--name', required=True, help='Subnet name')
@click.option('--description', help='Subnet description')
@click.option('--vlan', type=int, help='VLAN ID')
@click.option('--gateway', help='Gateway IP address')
def create_subnet(network, name, description, vlan, gateway):
    """Create a new subnet"""
    console.print(f"🌐 Creating subnet: {network}", style="bold blue")
    
    try:
        # Validate network CIDR
        network_obj = ipaddress.ip_network(network, strict=False)
        
        subnet_mgr = SubnetManager()
        
        subnet_data = {
            'network': str(network_obj),
            'name': name,
            'description': description or '',
            'vlan_id': vlan,
            'gateway': gateway or str(list(network_obj.hosts())[0])
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="Creating subnet...", total=None)
            
            result = subnet_mgr.create_subnet(subnet_data)
            
            if result.get('success'):
                subnet_id = result.get('subnet_id')
                console.print("✅ Subnet created successfully!", style="bold green")
                
                # Display subnet details
                table = Table(title=f"Subnet Details - {name}")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Subnet ID", str(subnet_id))
                table.add_row("Network", str(network_obj))
                table.add_row("Name", name)
                table.add_row("Available IPs", str(network_obj.num_addresses - 2))
                table.add_row("Gateway", subnet_data['gateway'])
                if vlan:
                    table.add_row("VLAN ID", str(vlan))
                
                console.print(table)
                
            else:
                console.print(f"❌ Failed to create subnet: {result.get('error')}", style="bold red")
                sys.exit(1)
                
    except ValueError as e:
        console.print(f"❌ Invalid network CIDR: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Error creating subnet: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option('--subnet', required=True, help='Subnet CIDR or ID')
@click.option('--hostname', help='Hostname for the allocation')
@click.option('--device-type', help='Device type (server, workstation, etc.)')
@click.option('--owner', help='Owner or department')
@click.option('--description', help='Description for the allocation')
@click.option('--static', is_flag=True, help='Create static allocation')
def allocate_ip(subnet, hostname, device_type, owner, description, static):
    """Allocate an IP address from a subnet"""
    console.print(f"📍 Allocating IP from subnet: {subnet}", style="bold blue")
    
    try:
        ipam_mgr = IPAMManager()
        
        allocation_data = {
            'subnet': subnet,
            'hostname': hostname,
            'device_type': device_type or 'unknown',
            'owner': owner,
            'description': description,
            'allocation_type': 'static' if static else 'dynamic'
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="Allocating IP address...", total=None)
            
            result = asyncio.run(ipam_mgr.allocate_ip(allocation_data))
            
            if result.get('success'):
                ip_address = result.get('ip_address')
                allocation_id = result.get('allocation_id')
                
                console.print("✅ IP address allocated successfully!", style="bold green")
                
                # Display allocation details
                table = Table(title="IP Allocation Details")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("IP Address", ip_address)
                table.add_row("Allocation ID", str(allocation_id))
                table.add_row("Subnet", subnet)
                table.add_row("Type", allocation_data['allocation_type'].title())
                if hostname:
                    table.add_row("Hostname", hostname)
                if device_type:
                    table.add_row("Device Type", device_type)
                if owner:
                    table.add_row("Owner", owner)
                
                console.print(table)
                
            else:
                console.print(f"❌ Failed to allocate IP: {result.get('error')}", style="bold red")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"❌ Error allocating IP: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument('ip_address')
@click.option('--force', is_flag=True, help='Force deallocation without confirmation')
def deallocate_ip(ip_address, force):
    """Deallocate an IP address"""
    if not force:
        if not click.confirm(f"Are you sure you want to deallocate {ip_address}?"):
            console.print("🚫 Deallocation cancelled", style="bold yellow")
            return
    
    console.print(f"🗑️ Deallocating IP address: {ip_address}", style="bold yellow")
    
    try:
        ipam_mgr = IPAMManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="Deallocating IP address...", total=None)
            
            result = asyncio.run(ipam_mgr.deallocate_ip(ip_address))
            
            if result.get('success'):
                console.print("✅ IP address deallocated successfully!", style="bold green")
                console.print(f"📋 Deallocation details: {result.get('message')}", style="bold cyan")
            else:
                console.print(f"❌ Failed to deallocate IP: {result.get('error')}", style="bold red")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"❌ Error deallocating IP: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option('--subnet', help='Filter by specific subnet')
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json', 'csv']), help='Output format')
def list_subnets(subnet, output_format):
    """List all subnets"""
    try:
        subnet_mgr = SubnetManager()
        
        if subnet:
            subnets = [subnet_mgr.get_subnet(subnet)]
            if not subnets[0]:
                console.print(f"❌ Subnet {subnet} not found", style="bold red")
                sys.exit(1)
        else:
            subnets = subnet_mgr.get_all_subnets()
        
        if output_format == 'table':
            table = Table(title="Network Subnets")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Network", style="yellow")
            table.add_column("Utilization", style="magenta")
            table.add_column("Available IPs", style="blue")
            table.add_column("VLAN", style="white")
            
            for subnet_data in subnets:
                if subnet_data:
                    utilization = subnet_data.get('utilization', 0)
                    util_color = "red" if utilization > 90 else "yellow" if utilization > 75 else "green"
                    
                    table.add_row(
                        str(subnet_data.get('id', '')),
                        subnet_data.get('name', ''),
                        subnet_data.get('network', ''),
                        f"{utilization:.1f}%",
                        str(subnet_data.get('available_ips', 0)),
                        str(subnet_data.get('vlan_id', 'N/A')),
                        style=util_color if utilization > 75 else None
                    )
            
            console.print(table)
            
        elif output_format == 'json':
            import json
            console.print(json.dumps([s for s in subnets if s], indent=2))
            
        elif output_format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'name', 'network', 'utilization', 'available_ips', 'vlan_id'])
            writer.writeheader()
            
            for subnet_data in subnets:
                if subnet_data:
                    writer.writerow({
                        'id': subnet_data.get('id'),
                        'name': subnet_data.get('name'),
                        'network': subnet_data.get('network'),
                        'utilization': f"{subnet_data.get('utilization', 0):.1f}%",
                        'available_ips': subnet_data.get('available_ips'),
                        'vlan_id': subnet_data.get('vlan_id', 'N/A')
                    })
            
            console.print(output.getvalue())
            
    except Exception as e:
        console.print(f"❌ Error listing subnets: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option('--subnet', help='Scan specific subnet (CIDR format)')
@click.option('--discovery-type', default='full', 
              type=click.Choice(['ping', 'arp', 'snmp', 'full']), help='Discovery method')
@click.option('--update-database', is_flag=True, help='Update database with discoveries')
def discover(subnet, discovery_type, update_database):
    """Discover devices on the network"""
    console.print("🔍 Starting network discovery...", style="bold blue")
    
    try:
        discovery_engine = DiscoveryEngine()
        
        discovery_params = {
            'subnet': subnet,
            'discovery_type': discovery_type,
            'update_database': update_database
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="Discovering devices...", total=None)
            
            result = asyncio.run(discovery_engine.discover_devices(discovery_params))
            
            if result.get('success'):
                devices = result.get('devices', [])
                console.print(f"✅ Discovery completed! Found {len(devices)} devices", style="bold green")
                
                if devices:
                    # Display discovered devices
                    table = Table(title="Discovered Devices")
                    table.add_column("IP Address", style="cyan")
                    table.add_column("MAC Address", style="green")
                    table.add_column("Hostname", style="yellow")
                    table.add_column("Vendor", style="magenta")
                    table.add_column("Status", style="blue")
                    
                    for device in devices[:20]:  # Show first 20 devices
                        table.add_row(
                            device.get('ip_address', 'Unknown'),
                            device.get('mac_address', 'Unknown'),
                            device.get('hostname', 'Unknown'),
                            device.get('vendor', 'Unknown'),
                            device.get('status', 'Unknown')
                        )
                    
                    console.print(table)
                    
                    if len(devices) > 20:
                        console.print(f"... and {len(devices) - 20} more devices", style="bold cyan")
                
                # Display summary
                console.print(Panel(
                    f"[bold green]Discovery Summary[/bold green]\n"
                    f"Total devices found: {len(devices)}\n"
                    f"Discovery method: {discovery_type}\n"
                    f"Database updated: {'Yes' if update_database else 'No'}\n"
                    f"Scan duration: {result.get('duration', 'Unknown')}"
                ))
                
            else:
                console.print(f"❌ Discovery failed: {result.get('error')}", style="bold red")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"❌ Error during discovery: {e}", style="bold red")
        sys.exit(1)


@cli.command()
def check_conflicts():
    """Check for IP address conflicts"""
    console.print("⚠️ Checking for IP address conflicts...", style="bold yellow")
    
    try:
        ipam_mgr = IPAMManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="Scanning for conflicts...", total=None)
            
            result = asyncio.run(ipam_mgr.check_conflicts())
            
            if result.get('success'):
                conflicts = result.get('conflicts', [])
                
                if conflicts:
                    console.print(f"⚠️ Found {len(conflicts)} IP conflicts!", style="bold red")
                    
                    # Display conflicts
                    table = Table(title="IP Address Conflicts")
                    table.add_column("IP Address", style="cyan")
                    table.add_column("Allocated To", style="green")
                    table.add_column("Detected Device", style="yellow")
                    table.add_column("Conflict Type", style="red")
                    table.add_column("Last Seen", style="magenta")
                    
                    for conflict in conflicts:
                        table.add_row(
                            conflict.get('ip_address', ''),
                            conflict.get('allocated_to', 'Unknown'),
                            conflict.get('detected_device', 'Unknown'),
                            conflict.get('conflict_type', 'Unknown'),
                            conflict.get('last_seen', 'Unknown')
                        )
                    
                    console.print(table)
                else:
                    console.print("✅ No IP conflicts detected!", style="bold green")
                
            else:
                console.print(f"❌ Conflict check failed: {result.get('error')}", style="bold red")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"❌ Error checking conflicts: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option('--subnet', help='Generate report for specific subnet')
@click.option('--format', 'output_format', default='table',
              type=click.Choice(['table', 'json', 'html']), help='Report format')
@click.option('--output', help='Output file path')
def generate_report(subnet, output_format, output):
    """Generate utilization report"""
    console.print("📊 Generating utilization report...", style="bold blue")
    
    try:
        from smart_ipam.utils.reporting import ReportGenerator
        
        report_gen = ReportGenerator()
        
        report_params = {
            'subnet': subnet,
            'format': output_format,
            'include_devices': True,
            'include_history': True
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(description="Generating report...", total=None)
            
            result = report_gen.generate_utilization_report(report_params)
            
            if result.get('success'):
                report_data = result.get('report')
                
                if output:
                    # Save to file
                    with open(output, 'w') as f:
                        if output_format == 'json':
                            import json
                            json.dump(report_data, f, indent=2)
                        elif output_format == 'html':
                            f.write(report_data.get('html_content', ''))
                        else:
                            f.write(str(report_data))
                    
                    console.print(f"✅ Report saved to: {output}", style="bold green")
                else:
                    # Display on console
                    if output_format == 'table':
                        # Create summary table
                        table = Table(title="Network Utilization Summary")
                        table.add_column("Metric", style="cyan")
                        table.add_column("Value", style="green")
                        
                        summary = report_data.get('summary', {})
                        table.add_row("Total Subnets", str(summary.get('total_subnets', 0)))
                        table.add_row("Total IPs", str(summary.get('total_ips', 0)))
                        table.add_row("Allocated IPs", str(summary.get('allocated_ips', 0)))
                        table.add_row("Available IPs", str(summary.get('available_ips', 0)))
                        table.add_row("Average Utilization", f"{summary.get('avg_utilization', 0):.1f}%")
                        
                        console.print(table)
                    else:
                        import json
                        console.print(json.dumps(report_data, indent=2))
                
            else:
                console.print(f"❌ Report generation failed: {result.get('error')}", style="bold red")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"❌ Error generating report: {e}", style="bold red")
        sys.exit(1)


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n🛑 Operation cancelled by user", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="bold red")
        sys.exit(1)
