require_relative '../../lib/utilities/json_utilities'
require 'mechanize'
require 'logger'

class MechanizeCustomized < Mechanize

  ##########################################################
  # Customized Mechanize that it would create a log with:
  # Time Stamp
  # HTTP request's (Response code, Method, URI, timing, params [first 30 chars], cookie [first 30 chars].

  def initialize
    @log_params_length = 30
    @log_cookie_length = 20
    @log_tmp_file = Dir.pwd + '/tmp/status_log.csv'
    super
  end

  # Hacked 'get' to add custom logs
  def get(uri, parameters = [], referer = nil, headers = {})
    @start_time = Time.now
    @method = 'GET'
    @parameters = parameters.to_s[0..@log_params_length]
    @cookie = cookies[0].to_s[0..@log_cookie_length]
    super
  end

  # Hacked 'post' to add custom logs
  def post (uri, query = {}, headers = {})
    @start_time = Time.now
    @method = 'POST'
    @parameters = query.to_s[0..@log_params_length]
    @cookie = cookies[0].to_s[0..@log_cookie_length]
    super
  end

  # Hacked 'put' to add custom logs
  def put(uri, entity, headers = {})
    @start_time = Time.now
    @method = 'PUT'
    @parameters = entity.to_s[0..@log_params_length]
    @cookie = cookies[0].to_s[0..@log_cookie_length]
    super
  end

  # Hacked 'delete' to add custom logs
  def delete(uri, query_params = {}, headers = {})
    @start_time = Time.now
    @method = 'DELETE'
    @parameters = query_params.to_s[0..@log_params_length]
    @cookie = cookies[0].to_s[0..@log_cookie_length]
    super
  end

  # Hacked 'parse' to store custom logs
  def parse uri, response, body

    begin
      timing = @start_time.nil?? 'unknown' : ((Time.now - @start_time) * 1000).to_i.to_s + 'ms'
      @timing = timing
      method = @method.nil?? 'unknown': @method
      parameters = @parameters.nil?? 'None' : @parameters.gsub(',', ';')
      cookie = @cookie.nil?? 'None' : @cookie.gsub(',', ';')
      log = ::File.open(@log_tmp_file, 'a')
      if response.code == '500' or response.code == '503' or response.code == '502'
        headers = ''
        response.header.each {|key, value| headers = headers + "#{key}=#{value}; "}
        log.write "#{DateTime.now}, #{response.code}, #{method}, #{uri.to_s.gsub(',', ';')}, #{timing}, #{parameters}, #{cookie}, #{headers.gsub(',', ';')}, #{response.message.to_s.gsub(',', ';')}, #{response.body.to_s.gsub(',', ';')} \n"
      else
        log.write "#{DateTime.now}, #{response.code}, #{method}, #{uri.to_s.gsub(',', ';')}, #{timing}, #{parameters}, #{cookie} \n"
      end
      log.close
    rescue Exception => e
      # if there is error in logging, it just print out the error, the log to console instead of saving to file.
      # It would not stop the test process.
      puts "Exception in Forum custom test log: #{e}"
      puts "#{DateTime.now}, #{response.code}, #{method}, #{uri.to_s.gsub(',', ';')}, #{timing}, #{parameters}, #{cookie} \n"
    end

    def response_time
      @timing[0..-2].to_i
    end

    super

  end
end

module AgentHandler
  def self.setup(api_extend, user: nil, host: nil, login_host: nil, parser: JSONParser, redirect: true, log: false, proxy: nil)
    agent = MechanizeCustomized.new
    agent.follow_meta_refresh = true
    agent.redirect_ok = redirect
    agent.read_timeout = 100000  # Some work services are very slow to respond
    agent.pluggable_parser.default = parser if parser != nil
    if user != nil
      agent.extend(Forum::API::USER)
      if login_host.nil?
        agent.host = host
      else
        agent.host = login_host
      end
      agent.login_imata(user)
    end
    if log
      agent.log = Logger.new(STDERR)
    end

    if proxy != nil
      agent.set_proxy(proxy, 80)
    end
    api_extend.each {|api| agent.extend(api)}
    agent.host = host
    agent
  end
end


