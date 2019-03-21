require_relative '../support/junit_formatter'
require_relative '../spec_helper'
require_relative '../../lib/utilities/json_utilities'
require_relative '../../spec/support/env'
require_relative '../../spec/support/agent_handler'

require 'logger'
require 'pact'
require 'mechanize'
require 'ithaka_utilities'

if ENVIRONMENT == 'prod'
  raise('PACT of forum service was not designed for Production execution. It was not verified to be safe for real-user data.')
end

RSpec.configuration.add_formatter JunitFormatter, "./tmp/junit_reports/rspec_junit_result_#{Time.new.to_i}.xml"

def thread_safe_key
  "##forum-autokey-#{Thread.current.object_id}"
end

def authenticate(user)
  ENV[thread_safe_key] = user
end


class ForumAuthorizer
  AUTH_COOKIES = ['sharedshelf']

  attr :updated_cookies

  def initialize(app)
    @app = app

    forum_key = thread_safe_key
    if ENV.has_key?(forum_key)
      @updated_cookies = login_to_forum(ENV[forum_key])
    end
  end

  def call(env)
    logger = Logger.new(STDOUT)
    if @updated_cookies
      cookie_string = @updated_cookies.map {|c| c.to_s}.join('; ')
      logger.warn('Request altered by ForumAuthorizer')
      env.merge!('HTTP_COOKIE' => cookie_string)
    end
    @app.call(env)
  end

  private

  def login_to_forum(user)
    agent = Mechanize.new
    agent.follow_meta_refresh = true
    agent.redirect_ok = true
    agent.extend(Forum::API::USER)
    agent.host=BASE_APPSGATEWAY_URL
    agent.pluggable_parser.default = JSONParser
    agent.login_imata(user)
    cookies = agent.cookies
    cookies.select {|c| AUTH_COOKIES.include?(c.name)}
  end

end

Pact.service_provider 'forum-services' do
  app do
    reverse_proxy = Rack::ReverseProxy.new do
      reverse_proxy '/', ENV.fetch('PACT_PROVIDER_BASE_URL')
    end
    ForumAuthorizer.new(reverse_proxy)
  end
end

Pact.configure do | config |
  config.doc_generator = :markdown
end

Pact.service_consumer 'forum-ui' do
  has_pact_with 'forum-jobmanager-service' do
    mock_service :jobmanager_service do
      port 1267
      pact_specification_version "2.0.0"
    end
  end
end

Pact.provider_states_for 'forum-ui' do
  agent = Mechanize.new
  agent.follow_meta_refresh = true
  agent.redirect_ok = true
  agent.extend(Forum::API::USER)
  agent.host = BASE_SHAREDSHELF_URL
  agent.pluggable_parser.default = JSONParser
  agent
  
  set_up do
    #   generic for all forum-ui calls
  end

  tear_down do
    #   generic for all forum-ui calls

    # Remove any state stored in the ENV
    ENV.delete(thread_safe_key)
  end

  provider_state '' do
    no_op
  end

  provider_state 'jm_valid_input' do
    tear_down do
      agent = AgentHandler.setup([Forum::API::JOBMANAGER], host: BASE_JOBMANAGER_URL)
      resp = JSON.parse(response.body, :symbolize_names => true)
      id = resp[:data][:job_id]
      agent.purge_job(id, 'e%vLm&*jXTk8ZTsE')
    end
  end

  provider_state 'a job with a known id exists' do
    set_up do
      @agent = AgentHandler.setup([Forum::API::JOBMANAGER], host: BASE_JOBMANAGER_URL)
      response = @agent.create_job(email:'fsrv@ithaka.org', job_type:'BulkExport', notify:'True')
      @job_id = JSON.parse(response.body, :symbolize_names => true)[:data][:job_id]

      # DANGER!  Rewriting query string of PACT contract -- be careful
      puts 'WARNING - rewriting request query'
      puts "Original query: #{@request.query}"
      @request.instance_variable_set(:@query, @request.query.to_s.gsub(/\*\*known_id\*\*/, @job_id.to_s))
      puts "Rewritten query: #{@request.query}"
    end

    tear_down do
      @agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
    end
  end

  provider_state 'a job with a known id exists with no tear down' do
    set_up do
      @agent = AgentHandler.setup([Forum::API::JOBMANAGER], host: BASE_JOBMANAGER_URL)
      response = @agent.create_job(email:'fsrv@ithaka.org', job_type:'BulkExport', notify:'True')
      @job_id = JSON.parse(response.body, :symbolize_names => true)[:data][:job_id]

      # DANGER!  Rewriting query string of PACT contract -- be careful
      puts 'WARNING - rewriting request query'
      puts "Original query: #{@request.query}"
      @request.instance_variable_set(:@query, @request.query.to_s.gsub(/\*\*known_id\*\*/, @job_id.to_s))
      puts "Rewritten query: #{@request.query}"
    end
  end

end


module PACTExtensions
  # Monkey patching the PACT interaction builder
  #
  # If the PACT folks majorly change the interaction builder in the future
  # this will break.


  def request(method, path, params={}, headers={})
    method_sym = method.to_sym
    unless [:get, :put, :post, :head, :delete, :options].include? method_sym
      raise "'#{method}' is not a HTTP method I understand"
    end
    case method_sym
      when :post
        with({method: method_sym, path: path, body: params, headers: headers})
      when :put
        with({method: method_sym, path: path, body: params, headers: headers})
      else
        with({method: method_sym, path: path, query: params, headers: headers})
    end
  end

  def response(status=200, body=nil, headers={})
    will_respond_with({status: status, body: body, header: headers})
  end

  def verify_with(agent)
    req = interaction.request
    path = req.path.respond_to?(:generate) ? req.path.generate : req.path
    begin
      case req.method
        when 'head'
          agent.head agent.host + path, req.query.query, req.headers
        when 'get'
          agent.get agent.host + path, req.query.query, nil, req.headers
        when 'post'
          agent.post agent.host + path, _build_body(req), req.headers
        when 'put'
          agent.put agent.host + path, _build_body(req), req.headers
        when 'delete'
          agent.delete agent.host + path, req.query.query, req.headers
        else
          logger.error "Unknown HTTP method #{req.method}"
      end
    rescue Mechanize::ResponseCodeError => e
      raise e unless e.response_code == interaction.response[:status].to_s
    end
  end

  def _build_body(req)
    body = req.body
    puts body
    return body unless body.respond_to?(:to_hash)
    data = _build_concrete_hash(body)
    req.headers['Content-Type'] == 'application/json' ? data.to_json : data
  end

  def _build_concrete_hash(request_data)
    data = request_data.to_hash
    data.keys.each do |k|
      data[k] = data[k].contents if data[k].respond_to? :generate
      if data[k].respond_to? :to_hash
        data[k] = _build_concrete_hash data[k]
      end
    end
    data
  end

end

Pact::Consumer::InteractionBuilder.include(PACTExtensions)

# Here lies another PACT monkey patch, if things break in strange ways during a PACT or Ruby upgrade this
# is the place to look.
#
# We are patching PACT to make it fit our use case better.  Currently PACT expects state to be managed outside
# the request/response cycle.  This works well if the your service is coded in Ruby along with the PACT for the
# service.  It breaks down quickly if your service is external to Ruby.
#
# In setup/tear down methods, the request/response information will now be included in the object passed to the
# methods.  You may use it like so:
#
# provider_state 'my provider state' do
#
#   set_up do |state|
#     pp state.request
#   end
#
#   tear_down do |state|
#     pp state.response
#   end
#
# end
module Pact::Provider::TestMethods

      def replay_interaction interaction
        # If this interaction has a provider state, open the class and add request/response attributes
        # to the class.  Set the request attribute to the interaction request and call the provider
        # state setup method.
        provider_state = Pact.provider_world.provider_states.get(interaction.provider_state, :for => @ithaka_consumer)
        if provider_state
          provider_state.class.module_eval { attr_accessor :request, :response }
          provider_state.request = interaction.request
          Pact.configuration.provider_state_set_up.call(interaction.provider_state, @ithaka_consumer, @ithaka_options)
        end

        request = Pact::Provider::Request::Replayable.new(interaction.request)
        args = [request.path, request.body, request.headers]

        logger.info "Sending #{request.method.upcase} request to path: \"#{request.path}\" with headers: #{request.headers}, see debug logs for body"
        logger.debug "body :#{request.body}"
        response = self.send(request.method.downcase, *args)

        # If this interaction has a provider state, set the response attribute to the actual response and call the
        # provider tear down method.
        if provider_state
          provider_state.response = response
          Pact.configuration.provider_state_tear_down.call(interaction.provider_state, @ithaka_consumer, @ithaka_options)
        end

        logger.info "Received response with status: #{response.status}, headers: #{response.headers}, see debug logs for body"
        logger.debug "body: #{response.body}"
      end

      def set_up_provider_state provider_state_name, consumer, options = {}
        # Don't call the provider state setup here, simply store the information for use in the
        # replay_interaction method
        @ithaka_consumer = consumer
        @ithaka_options = options
      end

      def tear_down_provider_state provider_state_name, consumer, options = {}
        # Don't call the provider tear down as we already did so in the
        # replay_interaction method

        # NOOP
      end

end
