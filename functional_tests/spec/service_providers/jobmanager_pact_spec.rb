require_relative 'pact_helper'
require_relative '../../lib/pact_payloads/jobmanager_req_and_resp'
require_relative '../../spec/support/agent_handler'

describe Forum::API::JOBMANAGER, :pact => true do
  payload = Pact::Payloads::Forum::API::JOBMANAGER
  let(:agent) {AgentHandler.setup([Forum::API::JOBMANAGER], host: jobmanager_service.mock_service_base_url)}

  describe 'Jobmanager service' do

    describe 'API - /status' do
      it 'returns 200 response with job details for valid id' do
        jobmanager_service.upon_receiving('valid id').
            request(:get, '/status', { 'id' => '1'} ).
            response(200, payload.status_contract_response).
            verify_with(agent)
      end
    end

    describe 'API - /new' do
      it 'returns 200 response with valid job parameter for create job' do
        jobmanager_service.upon_receiving('jm_valid_input').
            request(:get, '/new', payload.newjob_contract_params).
            response(200, Pact.like("{\"status\":\"Success\",\"data\":{\"job_id\":2004}}")).
            verify_with(agent)
      end
    end

    describe 'API - /purge' do
      it 'purges the job and returns a success status' do
        # The id here will be replaced with the id of an actual job
        jobmanager_service.given('a job with a known id exists with no tear down').
            upon_receiving('a request to remove job permanently').
            request(:get, '/purge', {id: '**known_id**', auth_key: 'e%vLm&*jXTk8ZTsE'}).
            response(200, Pact.like("{\"status\":\"Success\"}")).
            verify_with(agent)
      end
    end

    describe 'API - /delete' do
      it 'deletes the job and returns a success status' do
        # The id here will be replaced with the id of an actual job
        jobmanager_service.given('a job with a known id exists').
            upon_receiving('a request to set deleted status of job').
            request(:get, '/delete', {id: '**known_id**', message: 'Problem with processing'}).
            response(200, Pact.like("{\"status\":\"Success\"}")).
            verify_with(agent)
      end
    end

    describe 'API - /update' do
      it 'updates the job and returns a success status' do
        # The id here will be replaced with the id of an actual job
        jobmanager_service.given('a job with a known id exists').
            upon_receiving('a request to update the progress of job').
            request(:get, '/update', {id: '**known_id**', percentage: '50'}).
            response(200, Pact.like("{\"status\":\"Success\"}")).
            verify_with(agent)
      end
    end

    describe 'API - /completed' do
      it 'marks the job as completed and returns a success status' do
        # The id here will be replaced with the id of an actual job
        jobmanager_service.given('a job with a known id exists').
            upon_receiving('mark job status as completed').
            request(:get, '/completed', {id: '**known_id**', message: 'Job completed'}).
            response(200, Pact.like("{\"status\":\"Success\"}")).
            verify_with(agent)
      end
    end

    describe 'API - /error' do
      it 'marks the job as error and return a status that it seccessfully marked the job as error' do
        # The id here will be replaced with the id of an actual job
        jobmanager_service.given('a job with a known id exists').
            upon_receiving('mark job status as failure').
            request(:get, '/error', {id: '**known_id**', message: 'Problem with processing'}).
            response(200, Pact.like("{\"status\":\"Success\"}")).
            verify_with(agent)
      end
    end

    describe 'API - /flip_notify' do
      it 'flips the notification to on or off' do
        # The id here will be replaced with the id of an actual job
        jobmanager_service.given('a job with a known id exists').
            upon_receiving('a request to update the notification status').
            request(:get, '/flip_notify', {id: '**known_id**', notify: 'False'}).
            response(200, Pact.like("{\"status\":\"Success\"}")).
            verify_with(agent)
      end
    end

  end
end