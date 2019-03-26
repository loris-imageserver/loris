# Forum Loris IIIF Testing Suite

The code under functional_tests is a Ruby Rspec test suite for the Loris IIIF service. 
The key feature of the Loris IIIF is to redirect request to either Sagoku or AWS to look for the iiif images. 


## Setup required to run this project

Follow the instructions on the [Ruby Tool Installation](https://wiki.jstor.org/display/SEQ/Tool+Installation+-+Ruby+and+RubyMine) wiki page to get this project set up

## Test Location
* RSpec Tests are located within the _**spec/**_ directory

## Environments Supported
* Stage - Default if no environment is specified
* Production 

## features/support/env.rb
This file handles several environmental setup processes for the tests:

* Environment variables
    * Variables such as Base URL
    * If there is no local config file, default values are provided.
    * The local settings will be overridden in Jenkins jobs with an environment variable that is passed via CLI
* Required gems
    * All gems required for all tests are referenced in this file
* Required library files

## spec/support/rspec_config.rb
This file handles the setup and teardown tasks for the RSpec tests. The environment constants are loaded from the env.rb file

## RSpec Tags

* `:no_prod`
    * Indicates a test that should not run on the Production environment under any circumstances
* `:no_stage`
    * Indicates a test that should not run on the Stage environment under any circumstances

## Executing Tests
1. RSpec tests
    * rspec path/to/spec/file.rb
2. Rake Task
    * bundle exec rake Namespace:Taskname 

## Built With
* Ruby
* RSpec
* AWS SDK S3
* Mechanize
* MySQL