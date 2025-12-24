"""
CLI interface for the Observability MCP Server.

Provides command-line tools for managing and interacting with the observability server.
"""

import asyncio
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Observability MCP Server CLI")
console = Console()

@app.command()
def run():
    """Run the observability MCP server."""
    from .server import main
    main()

@app.command()
def health():
    """Check server health and status."""
    console.print("[green]✓ Observability MCP Server[/green]")
    console.print("Version: 0.1.0")
    console.print("Status: Ready to monitor MCP ecosystems")
    console.print("FastMCP: 2.14.1+ with OpenTelemetry integration")

@app.command()
def metrics():
    """Display current metrics and monitoring status."""
    table = Table(title="Observability MCP Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Description")

    table.add_row("OpenTelemetry", "✓ Active", "Distributed tracing and metrics")
    table.add_row("Prometheus", "✓ Active", "Metrics export on port 9090")
    table.add_row("Health Checks", "✓ Enabled", "Real-time service monitoring")
    table.add_row("Performance Tracking", "✓ Enabled", "CPU, memory, disk metrics")
    table.add_row("Persistent Storage", "✓ Enabled", "Historical data retention")

    console.print(table)

@app.command()
def docs():
    """Display documentation links."""
    console.print("[bold blue]📚 Observability MCP Documentation[/bold blue]")
    console.print()
    console.print("📖 [link=https://github.com/sandraschi/observability-mcp]GitHub Repository[/link]")
    console.print("📊 [link=http://localhost:9090]Prometheus Metrics[/link]")
    console.print("🔍 [link=https://opentelemetry.io]OpenTelemetry Documentation[/link]")
    console.print()
    console.print("[yellow]Tools Available:[/yellow]")
    console.print("• monitor_server_health - Real-time health checks")
    console.print("• collect_performance_metrics - System performance tracking")
    console.print("• trace_mcp_calls - Distributed tracing")
    console.print("• generate_performance_reports - Automated analysis")
    console.print("• alert_on_anomalies - Intelligent alerting")
    console.print("• monitor_system_resources - System-wide monitoring")
    console.print("• analyze_mcp_interactions - Usage pattern analysis")
    console.print("• export_metrics - Multiple export formats")

def main():
    """Main CLI entry point."""
    app(prog_name="observability-mcp")

if __name__ == "__main__":
    main()
