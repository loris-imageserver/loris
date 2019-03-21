# Forum Job Manager Testing Suite

This project contains Cucumber and RSpec tests used by the FORUM Front-End and Back-End Teams

## Setup required to run this project

Follow the instructions on the [Ruby Tool Installation](https://wiki.jstor.org/display/SEQ/Tool+Installation+-+Ruby+and+RubyMine) wiki page to get this project set up

## Test Location
* Cucumber Tests are located within the _**features/**_ directory
* RSpec Tests are located within the _**spec/**_ directory

## Environments Supported

* QA
* Stage - Default if no environment is specified
* Production 

## features/support/env.rb

This file handles several environmental setup processes for the tests:

* Environment variables
    * Variables such as Base URL and Browser can be brought in from an external config file.
    * If there is no local config file, default values are provided.
    * The local settings will be overridden in Jenkins jobs with an environment variable that is passed via CLI
* Required gems
    * All gems required for all tests are referenced in this file
* Required library files

## spec/support/rspec_config.rb
This file handles the setup and teardown tasks for the RSpec tests. The environment constants are loaded from the env.rb file

## RSpec Tags

* `:browser`
    * Triggers the respective Before (and After) actions & creates browser object 
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
* Watir
* RSpec
* AWS SDK S3
* Mechanize
* MySQL