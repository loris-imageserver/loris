# This is used for upload the Forum BE team's customer HTTP response log to S3.
# This is expected to be executed once the test is completed in Jenkins.
# It would update the custom status log to S2 location defined in this file.
# The status log would record:
# 1. Time Stamp of the HTTP request.
# 2. The URI of the request.
# 3. The response code of the request.
# 4. The respone time of the request.
# 5. The first 30 chars of the parameter in the request.
# 6. The first 20 chars of the cookie of the request.


require 'bundler'
Bundler.require(:default)
require_relative '../../lib/utilities/utilities.rb'

# Where in S3 to put the status log file
s3_bucket = 'qa-shared-shelf-data-files'
s3_folder = 'Forum_service/status_log/'

##########################################################
# Setup the filename using the Environment (prod/stage) and Time Stamp
##########################################################
config_environment = 'unknown'
if File.exists?('../../env_config.json')
  env_config_file = Hash[JSON.parse(File.read('../../env_config.json')).map {|key, value| [key.to_sym, value]}]
  config_environment = env_config_file[:environment]
end
environment = ENV['ENVIRONMENT'] ? ENV['ENVIRONMENT'] : config_environment
filename = "status_log_#{DateTime.now.to_s.gsub('-','').gsub(':','')[0..-6]}_#{environment}.csv"

##########################################################
# Upload the file to s3_folder in s3_bucket defined above:
##########################################################
begin
  # Path of the file when running local
  File.rename('../../tmp/status_log.csv', "../../tmp/#{filename}")
  ITHAKA::S3Utilities.upload_to_s3( s3_bucket, '../../tmp/', filename, {:folder => s3_folder})
rescue
  # Path of the file when running from Jenkin
  File.rename('./tmp/status_log.csv', "./tmp/#{filename}")
  ITHAKA::S3Utilities.upload_to_s3(s3_bucket, './tmp/', filename, {:folder => s3_folder})
end
