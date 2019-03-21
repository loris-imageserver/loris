require_relative '../support/env'
require_relative '../../spec/support/agent_handler'
require_relative '../../lib/utilities/mailinator_utilities'
require 'rspec'

describe 'Job manager APIs' do

  api_extends = [Forum::API::JOBMANAGER]
  host = DIRECT_SERVICE==''? BASE_JOBMANAGER_URL : DIRECT_SERVICE

  let(:agent) {AgentHandler.setup(api_extends, host: host)}
  mail = MailinatorUtilities.new

  describe 'API - /status' do

    valid_id = 46
    valid_email = 'qashared001@gmail.com'

    test_json = {:status=>"Completed",
                 :last_updated=>"07/12/2018 20:03",
                 :message=>
                     "The selected media files from <strong>Demo VR Project</strong> have been zipped and are <strong><a href=\"http://sharedshelf.stage.artstor.org/download/bulk_export/sharedshelf_mediaexport_6b87f2da-6b37-4ed2-949e-98e509dd5546.zip\"; style=\"font-family: Times New Roman, Times, serif; font-size: 18px; line-height: 26px; color: #000000; text-decoration: underline;\" target=\"_blank\">ready for download.</a></strong>This link will expire in 3 days",
                 :job_type=>"BulkExport",
                 :submitted=>"07/12/2018 20:03",
                 :email=>"qashared001@gmail.com",
                 :notify=>true,
                 :percentage=>100,
                 :id=>46}

    failure_json = {
        "status":"Failure",
        "message":"Unable to find job(s)"
    }

    prod_json = {:status=>"Completed",
                 :last_updated=>"07/19/2018 21:21",
                 :message=>
                     "The selected media files from <strong>Demo VR Project</strong> have been zipped and are <strong><a href=\"http://catalog.sharedshelf.artstor.org/bulk_download/media_export_0d609b89-5e3f-4703-bd7e-b1d938056f21.zip\"; style=\"font-family: Times New Roman, Times, serif; font-size: 18px; line-height: 26px; color: #000000; text-decoration: underline;\" target=\"_blank\">ready for download.</a></strong>This link will expire in 3 days",
                 :job_type=>"BulkExport",
                 :submitted=>"07/19/2018 21:21",
                 :email=>"qashared001@gmail.com",
                 :notify=>true,
                 :percentage=>100,
                 :id=>46}

    response_json = ENVIRONMENT == 'prod'? prod_json : test_json

    context 'success cases' do

      it 'returns 200 valid response for valid job id', :aggregate_failures, :int  do
        response = agent.get_status(id: valid_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        expect(result[:data].first).to include(response_json)
      end

      it 'returns 200 valid response for all job status', :aggregate_failures do
        response = agent.get_status(email: valid_email)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        job = result[:data].select {|job| job[:id] == 46}
        expect(job.first).to include(response_json)
      end
    end

    context 'failure cases' do

      it 'returns 200 with invalid response for invalid job id', :aggregate_failures do
        response = agent.get_status(id: -1)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result).to eq(failure_json)
      end

      it 'returns 200 with invalid response for invalid email', :aggregate_failures  do
        response = agent.get_status(email: 'fsrv_not_existed1@mailinator.com')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result).to eq(failure_json)
      end
    end

  end

  describe 'API - /new' do

    valid_email = 'qashared001@gmail.com'

    context 'success cases' do

      after do
        # Deletes the job
        agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
      end

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.create_job(email: valid_email, job_type: 'OAI', notify:'true')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        @job_id = result[:data][:job_id]

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:job_type]).to eq("OAI")
        expect(data[:notify]).to eq(true)
      end

      it 'returns 200 valid response for invalid email id', :aggregate_failures  do
        response = agent.create_job(email: "fsrv_not_existed@mailinator.com", job_type: 'OAI', notify:'false')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        @job_id = result[:data][:job_id]

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq('fsrv_not_existed@mailinator.com')
        expect(data[:job_type]).to eq("OAI")
        expect(data[:notify]).to eq(false)
      end

      it 'returns 200 valid response for invalid email format', :aggregate_failures  do
        response = agent.create_job(email: "wrongformat", job_type: 'OAI', notify:'false')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        @job_id = result[:data][:job_id]

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq('wrongformat')
        expect(data[:job_type]).to eq("OAI")
        expect(data[:notify]).to eq(false)
      end
    end

    context 'failure cases' do

      it 'returns 200 Failure response for missing email', :aggregate_failures  do
        response = agent.create_job(job_type: 'OAI', notify:'false')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['email']")
      end

      it 'returns 200 Failure response for missing job_type', :aggregate_failures  do
        response = agent.create_job(email: valid_email, notify:'false')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['job_type']")
      end

      it 'returns 200 Failure response for missing notify', :aggregate_failures  do
        response = agent.create_job(email: valid_email,job_type: 'OAI')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['notify']")
      end

      it 'returns 200 Failure response for missing all parameters', :aggregate_failures  do
        response = agent.create_job()
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['email', 'job_type', 'notify']")
      end

    end

  end

  describe 'API - /purge' do

    valid_email = 'qashared001@gmail.com'

    failure_json = {
        "status":"Failure",
        "message":"Unable to find job(s)"
    }

    before do
      response = agent.create_job(email: valid_email, job_type: 'OAI', notify:'true')
      result = JSON.parse(response.body, :symbolize_names => true)
      @job_id = result[:data][:job_id]
    end

    context 'success cases' do

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result).to eq(failure_json)
      end

    end

    context 'failure cases' do

      it 'returns 200 failure response for invalid job id', :aggregate_failures  do
        response = agent.purge_job(id: -1, auth_key: 'e%vLm&*jXTk8ZTsE')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Unable to update database - bad job id?")

      end

      it 'returns 200 Failure response for invalid authkey', :aggregate_failures  do
        response = agent.purge_job(id: @job_id, auth_key: 'invalid_key')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Invalid auth_key provided")
      end

      it 'returns 200 Failure response for missing id', :aggregate_failures  do
        response = agent.purge_job(auth_key: 'e%vLm&*jXTk8ZTsE')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id']")
      end

      it 'returns 200 Failure response for missing authkey', :aggregate_failures  do
        response = agent.purge_job(id: @job_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['auth_key']")
      end

      it 'returns 200 Failure response for no input paramters', :aggregate_failures  do
        response = agent.purge_job()
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id', 'auth_key']")
      end

    end

  end

  describe 'API - /delete' do

    valid_email = 'qashared001@gmail.com'

    before do
      response = agent.create_job(email: valid_email, job_type: 'OAI', notify:'true')
      result = JSON.parse(response.body, :symbolize_names => true)
      @job_id = result[:data][:job_id]
    end

    after do
      # Deletes the job
      agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
    end

    context 'success cases' do

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.delete_job(id: @job_id, message: 'Job no more required, please delete')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Deleted')
        expect(data[:message]).to eq('Job no more required, please delete')
      end

    end

    context 'failure cases' do

      it 'returns 200 failure response for invalid job id', :aggregate_failures  do
        response = agent.delete_job(id: -1, message: 'Job no more required, please delete')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Unable to update database - bad job id?")

      end

      it 'returns 200 Failure response for missing id', :aggregate_failures  do
        response = agent.delete_job( message: 'Job no more required, please delete')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id']")
      end

      it 'returns 200 Failure response for missing message', :aggregate_failures  do
        response = agent.delete_job(id: @job_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['message']")
      end

      it 'returns 200 Failure response for no input paramters', :aggregate_failures  do
        response = agent.delete_job()
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id', 'message']")
      end

    end

  end

  describe 'API - /update' do

    valid_email = 'qashared001@gmail.com'

    before do
      response = agent.create_job(email: valid_email, job_type: 'OAI', notify:'true')
      result = JSON.parse(response.body, :symbolize_names => true)
      @job_id = result[:data][:job_id]
    end

    after do
      # Deletes the job
      agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
    end

    context 'success cases' do

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.update_job(id: @job_id, percentage: 50)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Active')
        expect(data[:percentage]).to eq(50)
      end

      it 'returns 200 valid response for reducing percentage from 50 to 20', :aggregate_failures, :int  do
        response = agent.update_job(id: @job_id, percentage: 50)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        response = agent.update_job(id: @job_id, percentage: 20)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Active')
        expect(data[:percentage]).to eq(20)
      end

    end

    context 'failure cases' do

      it 'returns 200 valid response for invalid percentage', :aggregate_failures do
        response = agent.update_job(id: @job_id, percentage: 150)
        result = JSON.parse(response.body, :symbolize_names => true)

        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Percentage not between 0 and 100")
      end

      it 'returns 200 failure response for invalid job id', :aggregate_failures  do
        response = agent.update_job(id: -1, percentage: 50)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Unable to update database - bad job id?")

      end

      it 'returns 200 Failure response for missing id', :aggregate_failures  do
        response = agent.update_job( percentage: 50)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id']")
      end

      it 'returns 200 Failure response for missing percentage', :aggregate_failures  do
        response = agent.update_job(id: @job_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['percentage']")
      end

      it 'returns 200 Failure response for no input paramters', :aggregate_failures  do
        response = agent.update_job()
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id', 'percentage']")
      end

    end

  end

  describe 'API - /completed' do

    mail_id = 'fsrv_jobmanager_completed'
    valid_email = "#{mail_id}@mailinator.com"

    before do
      response = agent.create_job(email: valid_email, job_type: 'OAI', notify:'true')
      result = JSON.parse(response.body, :symbolize_names => true)
      @job_id = result[:data][:job_id]
      mail.delete_all_messages(mail_id)
    end

    after do
      # Deletes the job
      agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
    end

    context 'success cases' do

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.completed_job(id: @job_id, message: "Job ID: #{@job_id} Completed with No Errors")
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Completed')
        expect(data[:message]).to eq("Job ID: #{@job_id} Completed with No Errors")
        expect(data[:percentage]).to eq(100)
        for i in 0..40 do
          if mail.get_inbox(mail_id).messages.first.nil?
            sleep 1
          else
            break
          end
        end
        expect(mail.get_inbox(mail_id).messages.first).not_to be(nil), 'Expected mail not received in Mailinator.'
        received_mail = mail.get_first_message(mail_id)
        expect(received_mail['subject']).to eq('Your Forum media files are ready'), 'not getting the email from Job Manager Completed, subject check'
        expect(received_mail['body'].to_s).to include("Job ID: #{@job_id} Completed with No Errors"), 'not getting the email from Job Manager Completed, body msg check'
        mail.delete_first_message(mail_id)
      end

      it 'returns 200 valid response for marking completed job completed again', :aggregate_failures  do
        response = agent.completed_job(id: @job_id, message: 'Completed with No Errors')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        response = agent.completed_job(id: @job_id, message: 'Completed with No Errors')
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Completed')
        expect(data[:message]).to eq('Completed with No Errors')
        expect(data[:percentage]).to eq(100)

      end

    end

    context 'failure cases' do

      it 'returns 200 failure response for invalid job id', :aggregate_failures  do
        response = agent.completed_job(id:-1, message: 'Completed with No Errors')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq('Unable to update database - bad job id?')

      end

      it 'returns 200 Failure response for missing id', :aggregate_failures  do
        response = agent.completed_job( message: 'Completed with No Errors')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq("Missing required parameters: ['id']")
      end

      it 'returns 200 Failure response for missing message', :aggregate_failures  do
        response = agent.completed_job(id: @job_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq("Missing required parameters: ['message']")
      end

      it 'returns 200 Failure response for no input paramters', :aggregate_failures  do
        response = agent.completed_job()
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq("Missing required parameters: ['id', 'message']")
      end

    end

  end

  describe 'API - /error' do

    mail_id = 'fsrv_jobmanager_error'
    valid_email = "#{mail_id}@mailinator.com"

    before do
      response = agent.create_job(email: valid_email, job_type: 'OAI', notify:'true')
      result = JSON.parse(response.body, :symbolize_names => true)
      @job_id = result[:data][:job_id]
      mail.delete_all_messages(mail_id)
    end

    after do
      # Deletes the job
      agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
    end

    context 'success cases' do

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.error_job(id: @job_id, message: "Job ID: #{@job_id} - Problem with processing")
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Error')
        expect(data[:message]).to eq("Job ID: #{@job_id} - Problem with processing")
        expect(data[:percentage]).to eq(100)

        for i in 0..40 do
          if mail.get_inbox(mail_id).messages.first.nil?
            sleep 1
          else
            break
          end
        end
        expect(mail.get_inbox(mail_id).messages.first).not_to be(nil), 'Expected mail not received in Mailinator.'
        received_mail = mail.get_first_message(mail_id)
        expect(received_mail['subject']).to eq('Your Forum media files are ready'), 'not getting the email from Job Manager Error, subject check'
        expect(received_mail['body'].to_s).to include("Job ID: #{@job_id} - Problem with processing"), 'not getting the email from Job Manager Error, body msg check'
        mail.delete_first_message(mail_id)
      end


      it 'returns 200 valid response for setting error status of failed job again', :aggregate_failures  do
        response = agent.error_job(id: @job_id, message: 'Problem with processing')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        response = agent.error_job(id: @job_id, message: 'Problem with processing')
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")

        search_response = agent.get_status(id: @job_id)
        result = JSON.parse(search_response.body, :symbolize_names => true)
        expect(search_response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        data = result[:data].first
        expect(data[:email]).to eq(valid_email)
        expect(data[:status]).to eq('Error')
        expect(data[:message]).to eq('Problem with processing')
        expect(data[:percentage]).to eq(100)
      end

    end

    context 'failure cases' do

      it 'returns 200 failure response for invalid job id', :aggregate_failures  do
        response = agent.error_job(id:-1, message: 'Problem with processing')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq('Unable to update database - bad job id?')

      end

      it 'returns 200 Failure response for missing id', :aggregate_failures  do
        response = agent.error_job( message: 'Problem with processing')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq("Missing required parameters: ['id']")
      end

      it 'returns 200 Failure response for missing message', :aggregate_failures  do
        response = agent.error_job(id: @job_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq("Missing required parameters: ['message']")
      end

      it 'returns 200 Failure response for no input paramters', :aggregate_failures  do
        response = agent.error_job()
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq('Failure')
        expect(result[:message]).to eq("Missing required parameters: ['id', 'message']")
      end

    end

  end

  describe 'API - /flip_notify' do

    valid_email = 'qashared001@gmail.com'

    before do
      response = agent.create_job(email: valid_email, job_type: 'BulkExport', notify:'true')
      result = JSON.parse(response.body, :symbolize_names => true)
      @job_id = result[:data][:job_id]
    end

    after do
      # Deletes the job
      agent.purge_job(id: @job_id, auth_key: 'e%vLm&*jXTk8ZTsE')
    end

    context 'success cases' do

      it 'returns 200 valid response for valid inputs id', :aggregate_failures, :int  do
        response = agent.flip_notify(id: @job_id, notify: 'False')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
      end

      it 'returns 200 valid response for flipping notify multiple times', :aggregate_failures  do
        response = agent.flip_notify(id: @job_id, notify: 'False')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
        response = agent.flip_notify(id: @job_id, notify: 'True')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Success")
      end

    end

    context 'failure cases' do

      it 'returns 200 valid response for invalid notify value', :aggregate_failures do
        response = agent.flip_notify(id: @job_id, notify: 'Invalid')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
      end

      it 'returns 200 failure response for invalid job id', :aggregate_failures  do
        response = agent.flip_notify(id: -1, notify: 'False')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Unable to update notify field")
      end

      it 'returns 200 Failure response for missing id', :aggregate_failures  do
        response = agent.flip_notify(notify: 'True')
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id']")
      end

      it 'returns 200 Failure response for missing notify', :aggregate_failures  do
        response = agent.flip_notify(id: @job_id)
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['notify']")
      end

      it 'returns 200 Failure response for no input parameters', :aggregate_failures  do
        response = agent.flip_notify
        result = JSON.parse(response.body, :symbolize_names => true)
        expect(response.code).to eq('200')
        expect(result[:status]).to eq("Failure")
        expect(result[:message]).to eq("Missing required parameters: ['id', 'notify']")
      end

    end

  end



end

