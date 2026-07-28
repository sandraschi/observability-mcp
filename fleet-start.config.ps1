# Per-repo fleet start config for observability-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'observability-mcp'
    BackendPort  = 12007
    FrontendPort = 12008
    HealthPath   = '/health'
    WebRoot      = 'D:\Dev\repos\observability-mcp\web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'observability_mcp.server:app'
        SyncExtras    = @('dev')
        Env           = @{ WEB_PORT = '12007' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
