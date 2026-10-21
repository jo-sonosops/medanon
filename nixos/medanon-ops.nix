# Ops stack for the medanon lab on a NixOS host:
# Docker, a GitHub Actions self-hosted runner, Prometheus, node exporter,
# Alertmanager and Grafana. Everything listens on 127.0.0.1 only; reach the
# UIs from the Fedora workstation through an SSH tunnel.
#
# Use: copy this file and medanon-alerts.yml next to configuration.nix, then
#   imports = [ ./medanon-ops.nix ];
# and run: sudo nixos-rebuild switch
{ pkgs, ... }:

let
  # CHANGE ME: your private GitHub repo.
  repoUrl = "https://github.com/CHANGE-ME/medanon";
in
{
  virtualisation.docker.enable = true;

  # ---------------------------------------------------------------- runner
  # The runner polls GitHub over outbound HTTPS. No inbound port is opened.
  # Token: fine-grained PAT, only this repo, "Administration: Read and write".
  #   sudo install -d -m 0700 /var/lib/secrets
  #   sudo install -m 0600 /dev/stdin /var/lib/secrets/medanon-runner-token
  #   (paste the token, Enter, Ctrl-D)
  services.github-runners.medanon = {
    enable = true;
    url = repoUrl;
    tokenFile = "/var/lib/secrets/medanon-runner-token";
    extraLabels = [ "nixos" ];
    replace = true;
    extraPackages = with pkgs; [ docker curl bash coreutils ];
    # Docker group membership is root-equivalent on this host. Acceptable for a
    # lab; in production prefer rootless Podman or a pull-based deploy agent.
    serviceOverrides = {
      SupplementaryGroups = [ "docker" ];
    };
  };

  # App runtime config, read by deploy.sh through docker --env-file.
  #   sudo install -d -m 0750 -g docker /var/lib/medanon
  #   printf 'MEDANON_SALT=%s\n' "$(head -c 32 /dev/urandom | base64)" \
  #     | sudo install -m 0640 -g docker /dev/stdin /var/lib/medanon/env

  # ------------------------------------------------------------ monitoring
  services.prometheus = {
    enable = true;
    listenAddress = "127.0.0.1";
    port = 9090;
    retentionTime = "15d";
    globalConfig.scrape_interval = "15s";

    scrapeConfigs = [
      {
        job_name = "medanon";
        static_configs = [ { targets = [ "127.0.0.1:8080" ]; } ];
      }
      {
        job_name = "node";
        static_configs = [ { targets = [ "127.0.0.1:9100" ]; } ];
      }
    ];

    # Checked with promtool at build time: a broken rule fails the rebuild,
    # not production.
    ruleFiles = [ ./medanon-alerts.yml ];

    alertmanagers = [
      { static_configs = [ { targets = [ "127.0.0.1:9093" ]; } ]; }
    ];

    exporters.node = {
      enable = true;
      listenAddress = "127.0.0.1";
      port = 9100;
      enabledCollectors = [ "systemd" ];
    };

    alertmanager = {
      enable = true;
      listenAddress = "127.0.0.1";
      port = 9093;
      configuration = {
        route = {
          receiver = "default";
          group_by = [ "alertname" ];
          group_wait = "30s";
          repeat_interval = "4h";
        };
        # Alerts show in the Alertmanager UI. Stretch goal: add a Telegram or
        # email receiver here.
        receivers = [ { name = "default"; } ];
      };
    };
  };

  # --------------------------------------------------------------- grafana
  # First switch: Grafana fails to start because the secret files do not exist
  # yet. That is expected. Then run:
  #   sudo install -d -o grafana -g grafana -m 0700 /var/lib/grafana-secrets
  #   head -c 32 /dev/urandom | base64 | sudo install -o grafana -g grafana -m 0400 /dev/stdin /var/lib/grafana-secrets/secret-key
  #   head -c 18 /dev/urandom | base64 | sudo tee /dev/stderr | sudo install -o grafana -g grafana -m 0400 /dev/stdin /var/lib/grafana-secrets/admin-password
  #   sudo systemctl restart grafana
  # (the admin password is printed once by the tee; save it)
  services.grafana = {
    enable = true;
    settings = {
      server = {
        http_addr = "127.0.0.1";
        http_port = 3000;
      };
      security = {
        admin_user = "admin";
        admin_password = "$__file{/var/lib/grafana-secrets/admin-password}";
        secret_key = "$__file{/var/lib/grafana-secrets/secret-key}";
      };
      analytics.reporting_enabled = false;
    };
    provision = {
      enable = true;
      datasources.settings.datasources = [
        {
          name = "Prometheus";
          type = "prometheus";
          uid = "prometheus";
          url = "http://127.0.0.1:9090";
          isDefault = true;
        }
      ];
      # Phase 4: after you build and export the dashboard, uncomment this and
      # put the JSON in ./dashboards/ next to this file.
      # dashboards.settings.providers = [
      #   { name = "medanon"; options.path = ./dashboards; }
      # ];
    };
  };
}
