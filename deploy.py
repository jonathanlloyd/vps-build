from dataclasses import dataclass, field
from typing import Any, Dict, List

import envpy
from fabric import Connection, Config

SECRETS = envpy.get_config({
    'HOST': envpy.Schema(
        value_type=str,
    ),
    'SUDO_USER': envpy.Schema(
        value_type=str,
    ),
    'SUDO_PASSWORD': envpy.Schema(
        value_type=str,
    ),
    'GH_ACCESS_TOKEN': envpy.Schema(
        value_type=str,
    ),
    'GOSHOOP_SECRET_KEY': envpy.Schema(
        value_type=str,
    ),
    'GOSHOOP_API_SECRET': envpy.Schema(
        value_type=str,
    ),
    'TWITTER_CONSUMER_KEY': envpy.Schema(
        value_type=str,
    ),
    'TWITTER_CONSUMER_SECRET': envpy.Schema(
        value_type=str,
    ),
    'TWITTER_ACCESS_KEY': envpy.Schema(
        value_type=str,
    ),
    'TWITTER_ACCESS_SECRET': envpy.Schema(
        value_type=str,
    ),
})


def log(message):
    print('=====>', message)

def ensure_dokku_installed(conn, desired_version):
    version = None
    result = conn.sudo('dokku --version', warn=True, hide='both')
    if result.ok:
        version_parts = result.stdout.split(' ')
        if len(version_parts) == 3:
            version = version_parts[2].strip()

    if version == desired_version:
        log(f'Dokku already installed - version = {version}')
        return
    elif version is not None and version != desired_version:
        log(f'Unexpected Dokku version. Wanted {desired_version} but got {version}')
        raise RuntimeError('Unexpected Dokku version - cannot automatically upgrade')
    else:
        log(f'Dokku not installed installing {desired_version}')
        conn.run(f'wget https://dokku.com/install/v{desired_version}/bootstrap.sh')
        conn.sudo('bash bootstrap.sh')

def ensure_dokku_git_authenticated(conn, domain=None, user=None, token=None):
    log(f'Setting git auth for {domain}')
    conn.sudo(f'dokku git:auth {domain} {user} {token}')

@dataclass
class DokkuPlugin:
    name: str
    repo_url: str

def ensure_dokku_plugins(conn, plugins):
    for plugin in plugins:
        ensure_dokku_plugin(conn, plugin)

def ensure_dokku_plugin(conn, plugin):
    log(f'Ensuring Dokku {plugin.name} plugin is installed')
    result = conn.sudo('dokku plugin:list', hide='both')
    rows = result.stdout.split('\n')
    is_installed = any([row.strip().startswith(plugin.name) for row in rows])
    if is_installed:
        log(f'{plugin.name} plugin is already installed')
    else:
        conn.sudo(f'dokku plugin:install {plugin.repo_url}')

def ensure_letsencrypt_cron_enabled(conn):
    conn.sudo('dokku letsencrypt:cron-job --add')

@dataclass
class DokkuApp:
    name: str
    repo_url: str
    commit: str
    domains: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    backing_services: List[str] = field(default_factory=list)

def ensure_dokku_apps(conn, apps):
    for app in apps:
        ensure_dokku_app(conn, app)

def ensure_dokku_app(conn, dokku_app):
    log(f'Ensuring {dokku_app.name} is installed at the correct version')

    # Ensure the app exists
    result = conn.sudo('dokku apps:list', hide='both')
    results_split = result.stdout.split('\n')
    if len(results_split) >= 1:
        apps_list = results_split[1:]
    else:
        apps_list = []

    if dokku_app.name in apps_list:
        log(f'{dokku_app.name} already exists')
    else:
        log(f'{dokku_app.name} does not exist - creating')
        conn.sudo(f'dokku apps:create {dokku_app.name}')

    # Ensure the backing services have been set up
    for service in dokku_app.backing_services:
        if service == 'postgres':
            log(f'Creating Postgres instance for {dokku_app.name}')
            service_name = f'{dokku_app.name}_postgres'
            result = conn.sudo(f'dokku postgres:list', hide='both')
            rows = [row.strip() for row in result.stdout.split('\n')]
            service_exists = any([row.startswith(service_name) for row in rows])

            if service_exists:
                log(f'{service_name} already exists')
            else:
                conn.sudo(f'dokku postgres:create {dokku_app.name}_postgres')

            result = conn.sudo(f'dokku postgres:linked {service_name} {dokku_app.name}', warn=True, hide='both')
            if 'is linked' in result.stdout:
                log(f'{service_name} already linked to {dokku_app.name}')
            else:
                conn.sudo(f'dokku postgres:link {dokku_app.name}_postgres {dokku_app.name}')
        else:
            raise RuntimeError(f'Unknown backing service {service}')

    # Ensure the app config is set
    if dokku_app.config:
        config_str = ' '.join([f'{key}={value}' for key, value in dokku_app.config.items()])
        conn.sudo(f'dokku config:set {dokku_app.name} {config_str}')

    # Ensure the correct git hash is deployed
    result = conn.sudo(f'dokku git:report {dokku_app.name}', hide='both')
    git_sha = None
    rows = [row.strip() for row in result.stdout.split('\n')]
    for row in rows:
        if row.startswith('Git sha'):
            row_parts = [part.strip() for part in row.split(':')]
            if len(row_parts) == 2 and row_parts[1] != '':
                git_sha = row_parts[1]
            break

    if git_sha == dokku_app.commit:
        log(f'Commit "{dokku_app.commit}" already deployed')
    else:
        log(f'Commit "{git_sha}" does not match desired "{dokku_app.commit}" - upgrading')
        conn.sudo(f'dokku git:sync --build {dokku_app.name} {dokku_app.repo_url} {dokku_app.commit}')

    # Set app domains
    log(f'Setting domains for {dokku_app.name}')
    domain_list = ' '.join(dokku_app.domains)
    conn.sudo(f'dokku domains:set {dokku_app.name} {domain_list}')

def ensure_gameideabot(
    conn,
    cron_user,
    cron_schedule,
    commit,
    consumer_key,
    consumer_secret,
    access_key,
    access_secret,
):
    log(f'Building gameideabot image {commit}')
    conn.sudo(
        f'docker build https://github.com/jonathanlloyd/gameideabot.git#{commit}'
        + f' --build-arg CONSUMER_KEY={consumer_key}'
        + f' --build-arg CONSUMER_SECRET={consumer_secret}'
        + f' --build-arg ACCESS_KEY={access_key}'
        + f' --build-arg ACCESS_SECRET={access_secret}'
        + f' -t jonathanlloyd.dev/gameideabot:{commit}',
        hide='both'
    )
    log(f'Setting up gameideabot cron entry for user {cron_user}')
    conn.sudo(
        f'crontab -u {cron_user} -l'
        + ' | grep -v "gameideabot"'
        + f' | crontab -u {cron_user} -'
    )
    conn.sudo(
        f'crontab -u {cron_user} -l ;'
        + f' echo "{cron_schedule} docker run --rm jonathanlloyd.dev/gameideabot:{commit}"'
        + f' | crontab -u {cron_user} -'
    )


if __name__ == '__main__':
    config = Config(overrides={'sudo': {'password': SECRETS['SUDO_PASSWORD']}})
    conn = Connection(host=SECRETS['HOST'], user=SECRETS['SUDO_USER'], config=config)
    ensure_dokku_installed(conn, '0.30.2')
    ensure_dokku_git_authenticated(
        conn,
        domain='github.com',
        user='jonathan',
        token=SECRETS['GH_ACCESS_TOKEN'],
    )
    ensure_dokku_plugins(conn, [
        DokkuPlugin(
            name='postgres',
            repo_url='https://github.com/dokku/dokku-postgres.git',
        ),
        DokkuPlugin(
            name='letsencrypt',
            repo_url='https://github.com/dokku/dokku-letsencrypt.git',
        ),
    ])
    ensure_letsencrypt_cron_enabled(conn)
    ensure_dokku_apps(conn, [
        DokkuApp(
            name='jonathanlloyd.dev',
            repo_url='https://github.com/jonathanlloyd/thisisjonathan.com.git',
            commit='3ae3e3f',
            domains=[
                'www.thisisjonathan.com',
                'www.jonathanlloyd.dev',
                'thisisjonathan.com',
                'jonathanlloyd.dev',
            ],
        ),
        DokkuApp(
            name='goshoop',
            repo_url='https://github.com/jonathanlloyd/goshoop.git',
            commit='65719f5',
            domains=['goshoop.jonathanlloyd.dev'],
            config={
                'HOST': 'goshoop.jonathanlloyd.dev',
                'API_SECRET': SECRETS['GOSHOOP_API_SECRET'],
                'SECRET_KEY': SECRETS['GOSHOOP_SECRET_KEY'],
                'INTERNAL_API_URL': 'https://goshoop.jonathanlloyd.dev/api/',
                'EXTERNAL_API_URL': 'https://goshoop.jonathanlloyd.dev/api/',
            },
            backing_services=['postgres'],
        ),
    ])

    ensure_gameideabot(
        conn,
        cron_user=SECRETS['SUDO_USER'],
        cron_schedule='0 */6 * * *',
        commit='5835b2c7d04399f29e151cb4a5ce6f7e52722de2',
        consumer_key=SECRETS['TWITTER_CONSUMER_KEY'],
        consumer_secret=SECRETS['TWITTER_CONSUMER_SECRET'],
        access_key=SECRETS['TWITTER_ACCESS_KEY'],
        access_secret=SECRETS['TWITTER_ACCESS_SECRET'],
    )

    log('Remaining manual tasks: enable letsencrypt, restore databases')
