# ********************************************************************
# **Required Gems**
# ********************************************************************
require 'bundler'
Bundler.require(:default)

# ********************************************************************
# **Local Environment Configuration**
# ********************************************************************
local_env_configs = {
    environment: 'stage',
    target_browser: 'chrome',
    browser_width: 1600,
    browser_height: 1000,
    ip_auth_proxy_url: 'apacheproxy01.acorn.cirrostratus.org',
    ip_auth_proxy_port: '80',
    no_ip_auth_proxy_url: 'apacheproxy02.acorn.cirrostratus.org',
    no_ip_auth_proxy_port: '80',
    direct_service: '',
    grid_url: nil
}
stage_environment = {
    base_kts_url: "https://forum-kts-service.apps.test.cirrostratus.org",
    base_gust_url: "https://forum-gust-service.apps.test.cirrostratus.org",
    base_oai_url: "https://forum-scs-service.apps.test.cirrostratus.org",
    base_jobmanager_url: "https://forum-job-manager-service.apps.test.cirrostratus.org",
    base_report_url: "http://ssinstreports.stage.artstor.org",
    base_oai_service_url: 'http://sharedshelf.stage.artstor.org',
    base_aves_url: "http://sharedshelf.stage.artstor.org:80",
    base_adam_url: "http://sharedshelf.stage.artstor.org:80",
    base_idp_ocr_url: "http://job-tracker.apps.test.cirrostratus.org:8080/",
    base_sharedshelf_url: 'http://sharedshelf.stage.artstor.org',
    base_sharedshelflogin_url: 'http://sharedshelf.stage.artstor.org/login.html',
    base_sharedshelfadmin_url: 'http://sharedshelf.stage.artstor.org/admin.html',
    base_artstor_url: 'http://www.artstor.org',
    base_aws_url: 'http://stage.artstor.org',
    base_awsadmin_url: 'http://admin.stage.artstor.org/satools/admin.html',
    base_sharedshelfcommons_url: 'http://sscommons.stage.artstor.org/openlibrary/',
    base_privacy_url: 'http://sharedshelf.stage.artstor.org/ARTstor_Privacy_Policy.pdf',
    base_api_url: 'http://catalog.sharedshelf.stage.artstor.org:4040/',
    base_stor_url: 'https://stor.stage.artstor.org',
    base_universalviewer_url: 'http://catalog.sharedshelf.stage.artstor.org/viewer/',
    base_sharedshelfuiu_url: 'http://test.forum.jstor.org',
    base_omeka_url: 'http://omekaapi.artstor.acit.com/womeka',
    base_omeka_key_url: '5de0717892653b2c52d9530ef51d84daab8e9348',
    base_aatservice_url: 'http://forum-vocab-service.apps.test.cirrostratus.org',
    base_tgnservice_url: 'http://forum-vocab-service.apps.test.cirrostratus.org',
    base_ccoservice_url: 'http://forum-vocab-service.apps.test.cirrostratus.org',
    base_nameservice_url: 'http://forum-vocab-service.apps.test.cirrostratus.org',
    base_imataservice_url: 'http://sharedshelf.stage.artstor.org',
    base_iiif_url: 'http://sharedshelf.stage.artstor.org',
    base_bulkexporter_url: 'http://forum-bulk-exporter-service.apps.test.cirrostratus.org',
    base_appsgateway_url: 'https://test.forum.jstor.org',
    base_artaa_url: 'http://art-aa-service.apps.test.cirrostratus.org',
    base_aiwreport_url: 'http://artstorcloudp.cloudapp.net/qa',
    base_iac_service_url: 'http://iac-service.apps.test.cirrostratus.org',
    base_forum_admin_uiu_url: 'http://test.forum.jstor.org/admin/',
    base_elastic_search_url: 'http://192.168.90.78:9200',
    base_aiw_record_builder_url: 'http://artstor-record-builder.apps.test.cirrostratus.org',
    base_superindex_url: 'http://super-index.apps.test.cirrostratus.org',
    base_nightly_etl_url: 'http://artstor-ssreports-nightly-etl.apps.test.cirrostratus.org'
}
prod_environment = {
    base_kts_url: "https://forum-kts-service.apps.prod.cirrostratus.org",
    base_gust_url: "https://forum-gust-service.apps.prod.cirrostratus.org",
    base_oai_url: "https://forum-scs-service.apps.prod.cirrostratus.org",
    base_aves_url: "http://forum.jstor.org:80",
    base_adam_url: "http://forum.jstor.org:80",
    base_jobmanager_url: "https://forum-job-manager-service.apps.prod.cirrostratus.org",
    base_report_url: "http://ssinstreports.artstor.org",
    base_oai_service_url: 'http://oai.forum.jstor.org',
    base_idp_ocr_url: "http://job-tracker.apps.prod.cirrostratus.org:8080/",
    base_sharedshelf_url: 'http://catalog.sharedshelf.artstor.org',
    base_sharedshelflogin_url: 'http://catalog.sharedshelf.artstor.org/login.html',
    base_sharedshelfadmin_url: 'http://catalog.sharedshelf.artstor.org/admin.html',
    base_artstor_url: 'http://www.artstor.org',
    base_aws_url: 'http://library.artstor.org/',
    base_awsadmin_url: 'http://admin.artstor.org/satools/admin.html',
    base_sharedshelfcommons_url: 'http://www.sscommons.org/openlibrary/',
    base_privacy_url: 'http://catalog.sharedshelf.artstor.org/ARTstor_Privacy_Policy.pdf',
    base_api_url: 'http://catalog.sharedshelf.artstor.org:4040/',
    base_stor_url: 'https://stor.artstor.org',
    base_universalviewer_url: '',
    base_omeka_url: 'http://omekaapi.artstor.acit.com/womeka',
    base_omeka_key_url: '5de0717892653b2c52d9530ef51d84daab8e9348',
    base_aatservice_url: 'https://forum-vocab-service.apps.prod.cirrostratus.org',
    base_tgnservice_url: 'https://forum-vocab-service.apps.prod.cirrostratus.org',
    base_ccoservice_url: 'https://forum-vocab-service.apps.prod.cirrostratus.org',
    base_nameservice_url: 'https://forum-vocab-service.apps.prod.cirrostratus.org',
    base_imataservice_url: 'https://forum.jstor.org',
    base_iiif_url: 'http://catalog.sharedshelf.artstor.org',
    base_bulkexporter_url: 'http://forum-bulk-exporter-service.apps.prod.cirrostratus.org',
    base_appsgateway_url: 'https://forum.jstor.org',
    base_artaa_url: 'http://art-aa-service.apps.prod.cirrostratus.org',
    base_sharedshelfuiu_url: 'http://new.forum.jstor.org',
    base_aiwreport_url: 'http://report.artstor.org/report',
    base_aiw_ccollection_url: 'http://artstor-ccollection-service.apps.prod.cirrostratus.org',
    base_iac_service_url: 'http://iac-service.apps.prod.cirrostratus.org',
    base_forum_admin_uiu_url: 'http://new.forum.jstor.org/admin/',
    base_elastic_search_url: 'http://192.168.90.77:9200',
    base_aiw_record_builder_url: 'http://artstor-record-builder.apps.prod.cirrostratus.org',
    base_superindex_url: 'http://super-index.apps.prod.cirrostratus.org',
    base_nightly_etl_url: 'http://artstor-ssreports-nightly-etl.apps.prod.cirrostratus.org'
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
url_keys = %w[sharedshelf sharedshelflogin sharedshelfadmin artstor aws oai awsadmin sharedshelfcommons privacy api stor universalviewer sharedshelfuiu gust iiif omeka omeka_key aatservice tgnservice imataservice appsgateway artaa kts aiwreport ccoservice nameservice idp_ocr oai_service bulkexporter jobmanager report aves iac_service elastic_search adam aiw_record_builder nightly_etl]

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
BROWSER_WIDTH = ENV['BROWSERWIDTH'] ? ENV['BROWSERWIDTH'].to_i : local_env_configs[:browser_width]
BROWSER_HEIGHT = ENV['BROWSERHEIGHT'] ? ENV['BROWSERHEIGHT'].to_i : local_env_configs[:browser_height]
ENVIRONMENT = ENV['ENVIRONMENT'] ? ENV['ENVIRONMENT'] : local_env_configs[:environment]
TARGET_BROWSER = ENV['TARGET_BROWSER'] ? ENV['TARGET_BROWSER'] : local_env_configs[:target_browser]
CUSTOM_USER_AGENT = ENV['CUSTOMUSERAGENT'] ? ENV['CUSTOMUSERAGENT'] : local_env_configs[:custom_user_agent]
IP_AUTH_PROXY_URL = ENV['IPAUTHPROXYURL'] ? ENV['IPAUTHPROXYURL'] : local_env_configs[:ip_auth_proxy_url]
IP_AUTH_PROXY_PORT = ENV['IPAUTHPROXYPORT'] ? ENV['IPAUTHPROXYPORT'] : local_env_configs[:ip_auth_proxy_port]
NO_IP_AUTH_PROXY_URL = ENV['NOIPAUTHPROXYURL'] ? ENV['NOIPAUTHPROXYURL'] : local_env_configs[:no_ip_auth_proxy_url]
NO_IP_AUTH_PROXY_PORT = ENV['NOIPAUTHPROXYPORT'] ? ENV['NOIPAUTHPROXYPORT'] : local_env_configs[:no_ip_auth_proxy_port]
BASE_SHAREDSHELFLOGIN_URL = ENV['BASE_SHAREDSHELFLOGIN_URL'] ? ENV['BASE_SHAREDSHELFLOGIN_URL'] : local_env_configs[:base_sharedshelflogin_url]
BASE_KTS_URL = ENV['BASE_KTS_URL'] ? ENV['BASE_KTS_URL'] : local_env_configs[:base_kts_url]
BASE_GUST_URL = ENV['BASE_GUST_URL'] ? ENV['BASE_GUST_URL'] : local_env_configs[:base_gust_url]
BASE_STOR_URL = ENV['BASE_STOR_URL'] ? ENV['BASE_STOR_URL'] : local_env_configs[:base_stor_url]
BASE_SUPERINDEX_URL = ENV['BASE_SUPERINDEX_URL'] ? ENV['BASE_SUPERINDEX_URL'] : local_env_configs[:base_superindex_url]
DIRECT_SERVICE = ENV['DIRECT_SERVICE'] ? ENV['DIRECT_SERVICE'] : local_env_configs[:direct_service]
PAGE_TIMEOUT = 45
CLEAR_DOWNLOAD_DIR = local_env_configs.has_key?(:clear_local_download_directory) ? local_env_configs[:clear_local_download_directory] : true
CHROME_DRIVER = ENV['CHROME_DRIVER']
ENABLE_UNTRUSTED_SITES = ENV['ENABLE_UNTRUSTED_SITES'] ? ENV['ENABLE_UNTRUSTED_SITES'] : false
CLEAR_LOCAL_S3_DATA_FOLDER = local_env_configs.has_key?(:clear_local_s3_data_folder) ? local_env_configs[:clear_local_s3_data_folder] : true
GRID_URL = ENV['GRID_URL'] ? ENV['GRID_URL'] : local_env_configs[:grid_url]

BROWSER_OPTIONS = {
    browser: TARGET_BROWSER,
    height: BROWSER_HEIGHT,
    width: BROWSER_WIDTH,
    max_tests_before_restart: 15,
    grid_url: GRID_URL
}
IS_CUCUMBER = !!(ENV['IS_CUCUMBER'] == 'true')

# ********************************************************************
# ** Set S3 Data File Bucket & Local Directory
# ********************************************************************
S3OBJ = Aws::S3::Resource.new(region: 'us-east-1')
S3_DATA_FILE_BUCKET = 'qa-shared-shelf-data-files'
DATA_FILE_LOCAL_DIR = './lib/s3_data/'
if Dir.exist?(DATA_FILE_LOCAL_DIR)
  FileUtils.rm_rf(Dir.glob(DATA_FILE_LOCAL_DIR + '*')) if CLEAR_LOCAL_S3_DATA_FOLDER
else
  Dir.mkdir(DATA_FILE_LOCAL_DIR)
end

# ********************************************************************
# ** Make generic download directory for browser interactions
# ********************************************************************
DOWNLOAD_DIR =  GRID_URL && RUBY_PLATFORM =~ /linux/ ? '/home/seluser/' : File.join(Dir.pwd, '/lib/downloads/')
if Dir.exist?(DOWNLOAD_DIR)
  FileUtils.rm_rf(Dir.glob(DOWNLOAD_DIR + '*')) if CLEAR_DOWNLOAD_DIR
else
  Dir.mkdir(DOWNLOAD_DIR)
end

# ********************************************************************
# **Required Library Files**
# ********************************************************************
if IS_CUCUMBER
  #World statements could go here
end