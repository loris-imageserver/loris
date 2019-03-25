require_relative '../support/env'
require_relative '../../spec/support/agent_handler'
require 'rspec'
require 'cgi'
require 'digest'

describe 'Loris IIIF APIs' do

  api_extends = [Forum::API::LORIS_IIIF]
  stor_api_extends = [Forum::API::STOR]
  host = DIRECT_SERVICE==''? BASE_IIIF_URL : DIRECT_SERVICE
  md5 = Digest::MD5.new

  let(:agent) {AgentHandler.setup(api_extends, host: host)}
  test_id = Time.now.to_i.to_s
  context 'Record on Sagoku:' do
    tmp_download_path = "#{Dir.pwd}/tmp/Sagoku_download_#{test_id}.jpg"
    uuid_test = '51d7db67-3dbf-4a04-b84b-3b6b05405988'
    date_path_test = '/2019/03/25/15/'

    uuid_prod = 'e14ae65d-9303-4173-adec-3b1d06735c4b'
    date_path_prod = '/2019/03/22/18/'

    uuid = ENVIRONMENT == 'prod'? uuid_prod : uuid_test
    date_path = ENVIRONMENT == 'prod'? date_path_prod : date_path_test

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
    uuid_test = 'dd881ba7-a695-4c04-a012-c8f0e346c313'
    date_path_test = '/2019/03/22/10/'
    md5_iiif_test = 'ce135931ca54851db2cdf906baf358c0'
    uuid_prod = 'ef3015fc-0fec-423f-9c52-4ff18b3090d7'
    date_path_prod = '/2019/03/22/14/'
    md5_iiif_prod = 'ce135931ca54851db2cdf906baf358c0'
    uuid = ENVIRONMENT == 'prod'? uuid_prod : uuid_test
    date_path = ENVIRONMENT == 'prod'? date_path_prod : date_path_test
    expected_iiif_md5 = ENVIRONMENT == 'prod'? md5_iiif_prod : md5_iiif_test

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
      expect(md5.hexdigest(File.read(tmp_download_path))).to eq(expected_iiif_md5)
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

  context 'newly uploaded records' do
    file = "#{Dir.pwd}/lib/data_files/elizabeth.jpg"
    full_image_md5 = '7d333f47c02bbb925c81e7356047d0e5'
    tmp_download_path = "#{Dir.pwd}/tmp/Sagoku_download_#{test_id}.jpg"


    before :all do
      # Post/Upload an image to Stor
      @agent = AgentHandler.setup(stor_api_extends, host: BASE_STOR_URL)
      resp = @agent.post_compound_img_to_stor(file).json
      expect(resp[:id]).not_to eq(nil), 'uuid is nil at upload response'
      @uuid = resp[:id]
      expect(resp[:SourceFile]).to include(@uuid), 'SourceFile empty or not contain uuid at upload response'
      @source_file = resp[:SourceFile]
      expect(resp[:md5sum]).to eq(full_image_md5), 'md5 in stor db not match expected md5 at upload response'
      yyyy = resp[:timestamp][6..9]
      mm = resp[:timestamp][0..1]
      dd = resp[:timestamp][3..4]
      tt = resp[:timestamp][11..12]
      @date_path = '/' + yyyy + '/' + mm + '/' + dd + '/' + tt + '/'

      #wait until pyrimidal completed
      for i in 0..15 do
        resp = @agent.get_asset_meta_data(@uuid).json
        if resp[:pyrimidal_completed]
          break
        else
          puts "Pyrimidal completed not = true yet - wait #{i} of 15"
          sleep 1
        end
      end

    end

    it 'returns iiif json data of new image record on Sagoku' do
      resp = agent.get_iiif_json_data(@date_path, @uuid)
      expect(resp.response["access-control-allow-origin"]).to eq('*'), 'Header required for cross-origin request was missing'
      expect(resp.json[:@id]).to include(CGI.escape(@date_path[1..-1]+@uuid))
      expect(resp.uri.to_s).to include(BASE_IIIF_URL)
    end

    it 'returns iiif new image of on Sagoku' do
      resp = agent.get_iiif_image_view(@date_path, @uuid)
      expect(resp.code).to eq('200')
      expect(resp.response["content-type"]).to eq('image/jpeg')
      expect(resp.response["content-length"]).to eq('23584')
      resp.save! tmp_download_path
      expect(md5.hexdigest(File.read(tmp_download_path))).to eq('6e99d6c4f383220904611ccdf601ebb7')
    end

  end
end

