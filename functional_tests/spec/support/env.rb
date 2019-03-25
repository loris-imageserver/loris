# ********************************************************************
# **Required Gems**
# ********************************************************************
require 'bundler'
Bundler.require(:default)
require 'ithaka_utilities'

# ********************************************************************
# **Local Environment Configuration**
# ********************************************************************
local_env_configs = {
    ip_auth_proxy_url: 'apacheproxy01.acorn.cirrostratus.org',
    ip_auth_proxy_port: '80',
    no_ip_auth_proxy_url: 'apacheproxy02.acorn.cirrostratus.org',
    no_ip_auth_proxy_port: '80',
    direct_service: '',
    environment: 'stage'
}
stage_environment = {
    base_appsgateway_url: 'https://test.forum.jstor.org'
}
prod_environment = {
    base_appsgateway_url: 'https://forum.jstor.org'
}

if File.exists?('env_config.json')
  env_config_file = Hash[JSON.parse(File.read('env_config.json')).map {|key, value| [key.to_sym, value]}]
  if env_config_file[:environment] == 'prod'
    local_env_configs.merge!(prod_environment)
  else
    local_env_configs.merge!(stage_environment)
  end
  local_env_configs.merge!(env_config_file)
elsif ENV['ENVIRONMENT'] == 'prod'
  local_env_configs.merge!(prod_environment)
else
  local_env_configs.merge!(stage_environment)
end

# ********************************************************************
# **Base URL Constant Creation**
#   Given a key of 'sharedshelf'
#     Sets a constant BASE_SHAREDSHELF_URL of
#       ENV['BASESHAREDSHELFURL'] if it exists
#       Otherwise sets it to local_env_configs[:base_sharedshelf_url]
#     Sets a constant BASE_SHAREDSHELF_URL_SECURE
#       from constant BASE_SHAREDSHELF_URL but with scheme of 'https'
# ********************************************************************
url_keys = %w[appsgateway]

begin
  url_keys.each do |key|
    target_key = "base_#{key}_url"
    constant_name = target_key.upcase
    env_name = constant_name.gsub('_', '')
    if ENV[env_name]
      Kernel.const_set(constant_name, URI.unescape(ENV[env_name]).to_s)
      pp "Using #{constant_name} at the following address: #{eval(constant_name)}"
    else
      Kernel.const_set(constant_name, local_env_configs[target_key.to_sym])
    end
    uri = URI(Kernel.const_get(constant_name))
    uri.scheme = 'https'
    Kernel.const_set("#{constant_name}_SECURE", uri.to_s)
  end
rescue
  raise "You did not set a global variable ENVIRONMENT for the OS (dev/qa/stage/demo/production) \nOR you have to create a env_config.json and put it in the project, the json file have the value: {\"target_browser\": \"chrome\",\"environment\": \"qa\"} "
end

# ********************************************************************
# **Other Constants**
#   In a Cloud Environment (CFN), URLs are determined dynamically
# ********************************************************************
ENVIRONMENT = ENV['ENVIRONMENT'] ? ENV['ENVIRONMENT'] : local_env_configs[:environment]
IP_AUTH_PROXY_URL = ENV['IPAUTHPROXYURL'] ? ENV['IPAUTHPROXYURL'] : local_env_configs[:ip_auth_proxy_url]
IP_AUTH_PROXY_PORT = ENV['IPAUTHPROXYPORT'] ? ENV['IPAUTHPROXYPORT'] : local_env_configs[:ip_auth_proxy_port]
NO_IP_AUTH_PROXY_URL = ENV['NOIPAUTHPROXYURL'] ? ENV['NOIPAUTHPROXYURL'] : local_env_configs[:no_ip_auth_proxy_url]
NO_IP_AUTH_PROXY_PORT = ENV['NOIPAUTHPROXYPORT'] ? ENV['NOIPAUTHPROXYPORT'] : local_env_configs[:no_ip_auth_proxy_port]
DIRECT_SERVICE = ENV['DIRECT_SERVICE'] ? ENV['DIRECT_SERVICE'] : local_env_configs[:direct_service]
PAGE_TIMEOUT = 45

# ********************************************************************
# **Service location from Eurkea **
# ********************************************************************
service = ITHAKA::ServiceLocation
env = ENVIRONMENT
env = 'test' if ENVIRONMENT == 'stage'
raise "unrecognized environment setting '#{env}'" if (env != 'prod' and env != 'test')
service.configuration.environment = env

BASE_JOBMANAGER_URL = service.get_host('forum-job-manager-service')
BASE_IIIF_URL = service.get_host('forum-iiif-service')
