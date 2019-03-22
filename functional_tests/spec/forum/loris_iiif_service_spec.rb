require_relative '../support/env'
require_relative '../../spec/support/agent_handler'
require 'rspec'
require 'cgi'

describe 'Loris IIIF APIs' do

  api_extends = [Forum::API::STOR]
  host = DIRECT_SERVICE==''? BASE_IIIF_URL : DIRECT_SERVICE

  let(:agent) {AgentHandler.setup(api_extends, host: host)}

  context 'Record on Sagoku:' do
    uuid = 'd0434e64-0793-4017-83f6-5895d82fd897'
    date_path = '/2019/03/19/17/'
    it 'is a nut' do
      resp = agent.get_iiif_json_data(date_path, uuid)
      expect(resp.response["access-control-allow-origin"]).to eq('*'), 'Header required for cross-origin request was missing'
      expect(resp.json[:@id]).to include(CGI.escape(date_path[1..-1]+uuid))
    end

    it 'returns size 0 image' do
      resp = agent.get_iiif_image_view(date_path, uuid)
      pp resp
    end
  end

  context 'Record on AWS: ' do

  end


end

