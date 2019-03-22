require_relative '../support/env'
require_relative '../../spec/support/agent_handler'
require 'rspec'
require 'cgi'
require 'digest'

describe 'Loris IIIF APIs' do

  api_extends = [Forum::API::STOR]
  host = DIRECT_SERVICE==''? BASE_IIIF_URL : DIRECT_SERVICE
  md5 = Digest::MD5.new

  let(:agent) {AgentHandler.setup(api_extends, host: host)}
  test_id = Time.now.to_i.to_s
  context 'Record on Sagoku:' do
    tmp_download_path = "#{Dir.pwd}/tmp/Sagoku_download_#{test_id}.jpg"
    uuid = 'd0434e64-0793-4017-83f6-5895d82fd897'
    date_path = '/2019/03/19/17/'

    it 'returns iiif json data of image record on Sagoku' do
      resp = agent.get_iiif_json_data(date_path, uuid)
      expect(resp.response["access-control-allow-origin"]).to eq('*'), 'Header required for cross-origin request was missing'
      expect(resp.json[:@id]).to include(CGI.escape(date_path[1..-1]+uuid))
      expect(resp.uri.to_s).to include(BASE_IIIF_URL)
    end

    it 'returns iiif image of on Sagoku' do
      resp = agent.get_iiif_image_view(date_path, uuid)
      expect(resp.code).to eq('200')
      expect(resp.response["content-type"]).to eq('image/jpeg')
      expect(resp.response["content-length"]).to eq('23584')
      resp.save! tmp_download_path
      expect(md5.hexdigest(File.read(tmp_download_path))).to eq('6e99d6c4f383220904611ccdf601ebb7')
    end
  end

  context 'Record on DataCenter: ' do
    tmp_download_path = "#{Dir.pwd}/tmp/DC_download_#{test_id}.jpg"
    uuid = 'dd881ba7-a695-4c04-a012-c8f0e346c313'
    date_path = '/2019/03/22/10/'

    it 'returns iiif json data of image record on DataCenter' do
      resp = agent.get_iiif_json_data(date_path, uuid)
      expect(resp.response["access-control-allow-origin"]).to eq('*'), 'Header required for cross-origin request was missing'
      expect(resp.json[:@id]).to include(date_path[1..-1]+uuid)
      expect(resp.uri.to_s).to include('dcstor')
    end

    it 'returns iiif image of on DataCenter' do
      resp = agent.get_iiif_image_view(date_path, uuid)
      expect(resp.code).to eq('200')
      expect(resp.response["content-type"]).to eq('image/jpeg')
      resp.save! tmp_download_path
      expect(md5.hexdigest(File.read(tmp_download_path))).to eq('c29ea1ad73e23489776a5428f2c59126')
    end
  end

  context 'failure cases:' do
    uuid = 'dd881ba7-a695-4c04-a012-c8f0e346c313'
    date_path = '/2019/03/22/11/'
    it 'returns 404 error iiif json data request if record not existed neither DC or Sagoku' do
      expect {agent.get_iiif_json_data(date_path, uuid)}.to raise_exception {|error|
        expect(error.response_code).to eq('404')}
    end

    it 'returns 404 error iiif image request if record not existed on neither DC or Sagoku' do
      expect {agent.get_iiif_json_data(date_path, uuid)}.to raise_exception {|error|
        expect(error.response_code).to eq('404')}
    end
  end
end

