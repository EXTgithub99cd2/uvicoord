{
  description = "Uvicoord - Uvicorn Coordinator for Python web applications";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # NixOS module for system-wide service
      nixosModule = { config, lib, pkgs, ... }:
        let
          cfg = config.services.uvicoord;
        in
        {
          options.services.uvicoord = {
            enable = lib.mkEnableOption "Uvicoord coordinator service";
            
            port = lib.mkOption {
              type = lib.types.port;
              default = 9000;
              description = "Port for the coordinator service";
            };
            
            configDir = lib.mkOption {
              type = lib.types.path;
              default = "/var/lib/uvicoord";
              description = "Directory for uvicoord configuration";
            };
            
            user = lib.mkOption {
              type = lib.types.str;
              default = "uvicoord";
              description = "User to run uvicoord as";
            };
            
            group = lib.mkOption {
              type = lib.types.str;
              default = "uvicoord";
              description = "Group to run uvicoord as";
            };
          };
          
          config = lib.mkIf cfg.enable {
            users.users.${cfg.user} = {
              isSystemUser = true;
              group = cfg.group;
              home = cfg.configDir;
              createHome = true;
            };
            
            users.groups.${cfg.group} = {};
            
            systemd.services.uvicoord = {
              description = "Uvicoord - Uvicorn Coordinator Service";
              after = [ "network.target" ];
              wantedBy = [ "multi-user.target" ];
              
              environment = {
                UVICOORD_CONFIG = "${cfg.configDir}/config.json";
              };
              
              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = cfg.group;
                ExecStart = "${self.packages.${pkgs.system}.default}/bin/uvicoord-service";
                Restart = "on-failure";
                RestartSec = 5;
                
                # Hardening
                NoNewPrivileges = true;
                ProtectSystem = "strict";
                ProtectHome = true;
                ReadWritePaths = [ cfg.configDir ];
                PrivateTmp = true;
              };
            };
          };
        };
    in
    {
      nixosModules.default = nixosModule;
      nixosModules.uvicoord = nixosModule;
    } //
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pythonPackages = pkgs.python312Packages;
        
        uvicoord = pythonPackages.buildPythonPackage rec {
          pname = "uvicoord";
          version = "0.2.0";
          format = "pyproject";
          
          src = ../core;
          
          nativeBuildInputs = with pythonPackages; [
            hatchling
          ];
          
          propagatedBuildInputs = with pythonPackages; [
            fastapi
            uvicorn
            httpx
            typer
            pydantic
            psutil
            rich
          ];
          
          pythonImportsCheck = [ "uvicoord" ];
        };
      in
      {
        packages.default = uvicoord;
        packages.uvicoord = uvicoord;
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python312
            python312Packages.pip
            python312Packages.virtualenv
          ];
        };
        
        apps.default = {
          type = "app";
          program = "${uvicoord}/bin/uvicoord";
        };
        
        apps.service = {
          type = "app";
          program = "${uvicoord}/bin/uvicoord-service";
        };
      }
    );
}
