"""
Fabric script to install graphite and statsd on a debian based system
To use the script without user interaction, make sure your local user exists on the target machine 
copy your public ssh-key with ssh-copy-id, or modify env.user to your needs.


"""


from fabric.api import *
from fabric.operations import put
from fabric.contrib.files import exists, upload_template


TARGET_HOST = "put your host ip/dns here"


env.graphite_dir = "/opt/graphite/webapp/graphite"
env.statsd_dir = "/opt/graphite/statsd"




def dev():
    """run commands on localhost: need write perms to /opt/graphite"""
    env.run = local
    env.host = "localhost"


def vagrant():
    """run commands on a vagrant vm"""
    env.run = run
    env.hosts = ['127.0.0.1:2222']
    result = local('vagrant ssh_config | grep IdentityFile', capture=True)
    env.key_filename = result.split()[1]
    env.home = "/home/vagrant"
    env.user = "vagrant"

def target():
    """run commands on your target host"""
    env.run = run
    env.hosts = [TARGET_HOST]
    env.home = "~%s" % env.user








# internal commands
def _install_req():
    env.run("sudo apt-get update -qq && sudo aptitude install python libcairo2-dev python-cairo python-software-properties -q -y ")

def _create_ve():
    if not exists("%s/virtualenvs/graphite" % env.home):
        env.run("""
                source ~/.bash_profile &&
                mkvirtualenv -q graphite"""
        )

def _ve_run(cmd):
    env.run("""
               source ~/.bash_profile &&
               workon graphite &&
               %s
               """ % (cmd)
    )

def _configure_django_env():
    env.run("sudo aptitude install nginx supervisor")
    env.run("sudo pip install meld3") # fixes supervisor bug
    env.run("sudo /etc/init.d/supervisor stop && sleep 3 && sudo /etc/init.d/supervisor start")

    # configure supervisor/gunicorn
    upload_template('conf/supervisor/graphite.conf','/etc/supervisor/conf.d/graphite.conf', {'home': env.home } , use_sudo=True, backup=False)
    env.run('sudo supervisorctl reload')

    # configure nginx

    upload_template('conf/nginx/graphite','/etc/nginx/sites-enabled/graphite', {'home':env.home}, use_sudo=True, backup=False)
    env.run('sudo /etc/init.d/nginx restart')

def _configure_graphite():
    with cd('/opt/graphite/conf'):
        env.run('ln -sf carbon.conf.example carbon.conf')
        env.run('ln -sf dashboard.conf.example dashboard.conf')
        env.run('ln -sf relay-rules.conf.example relay-rules.conf')

    put('conf/graphite/storage-schemas.conf','/opt/graphite/conf/storage-schemas.conf', use_sudo=False)


def carbon_restart():
    env.run('sudo /opt/graphite/bin/carbon-cache.py stop && sudo /opt/graphite/bin/carbon-cache.py start')


def _install_nodejs():
    env.run('sudo add-apt-repository ppa:chris-lea/node.js && sudo apt-get update -qq ')
    env.run('sudo apt-get install nodejs -q -y')
 

def _install_statsd():
    if not exists(env.statsd_dir):
        with cd('/opt/graphite'):
            run('git clone git://github.com/etsy/statsd.git statsd')
    else:
        with cd(env.statsd_dir):
            run('git pull')

    _install_nodejs()

    put('conf/supervisor/statsd.conf','/etc/supervisor/conf.d/statsd.conf', use_sudo=True)
    env.run('sudo supervisorctl reload')
    put('conf/statsd_settings.js', env.statsd_dir+'/statsd_settings.js')


def deploy():
    """install graphite web"""
    env.run('sudo mkdir -p /opt/graphite && sudo chmod 777 /opt/graphite') # change permissions as needed
    _install_req()
    _create_ve()
    _ve_run("pip install graphite-web django carbon gunicorn python-memcached whisper")
    with cd(env.graphite_dir):
        _ve_run("python manage.py syncdb --noinput")

    _configure_django_env()
    _configure_graphite()

    _install_statsd()
    carbon_restart()






        



    
