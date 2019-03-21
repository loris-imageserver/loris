require 'pact/consumer/rspec'

module Pact
  module Payloads
    module Forum
      module API
        module JOBMANAGER

          def self.status_contract_response
            "{\"status\":\"Success\",\"data\":[{\"status\":\"Completed\",\"last_updated\":\"12\\/13\\/2014 20:15\",\"message\":\"The selected media files from <strong>Demo VR Project<\\/strong> have been zipped and are <strong><a href=\\\"http:\\/\\/sharedshelf.artstor.org\\/download\\/bulk_export\\/sharedshelf_mediaexport_23001509-d847-4a28-802b-384af638e306.zip\\\"; style=\\\"font-family: Times New Roman, Times, serif; font-size: 18px; line-height: 26px; color: #000000; text-decoration: underline;\\\" target=\\\"_blank\\\">ready for download.<\\/a><\\/strong>This link will expire in 3 days\",\"job_type\":\"BulkExport\",\"submitted\":\"12\\/13\\/2014 20:15\",\"email\":\"qasam001@artstor.org\",\"notify\":true,\"percentage\":100,\"id\":1}]}"
          end

          def self.newjob_contract_params
            {
                'email' => 'qasam001@artstor.org',
                'job_type' => 'OAI',
                'notify' => 'true'
            }
          end

        end
      end
    end
  end
end
