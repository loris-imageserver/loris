=begin

Copyright (c) 2012, Nathaniel Ritmeyer
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

3. Neither the name Nathaniel Ritmeyer nor the names of contributors to
this software may be used to endorse or promote products derived from this
software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

=end

require 'builder'

class JunitFormatter
  RSpec::Core::Formatters.register self, :example_passed, :example_failed, :example_pending, :dump_summary

  def initialize(output)
    @output             = output
    @test_suite_results = {}
    @builder            = Builder::XmlMarkup.new :indent => 2
  end

  def example_passed(example_notification)
    add_to_test_suite_results example_notification
  end

  def example_failed(example_notification)
    add_to_test_suite_results example_notification
  end

  def example_pending(example_notification)
    add_to_test_suite_results example_notification
  end

  def dump_summary(summary)
    build_results(summary.duration, summary.examples.size, summary.failed_examples.size, summary.pending_examples.size)
    @output.puts @builder.target!
  end

  protected

  def add_to_test_suite_results(example_notification)
    suite_name                      = JunitFormatter.root_group_name_for example_notification
    @test_suite_results[suite_name] = [] unless @test_suite_results.keys.include? suite_name
    @test_suite_results[suite_name] << example_notification.example
  end

  def failure_details_for(example)
    exception           = example.exception
    formatted_backtrace = RSpec::Core::BacktraceFormatter.new.format_backtrace exception.backtrace
    exception.nil? ? '' : "#{exception.message}\n#{formatted_backtrace}"
  end

  # utility methods

  def self.count_in_suite_of_type(suite, test_case_result_type)
    suite.select { |example| example.metadata[:execution_result].status == test_case_result_type }.size
  end

  def self.root_group_name_for(example_notification)
    example_notification.example.metadata[:example_group][:full_description]
  end

  # methods to build the xml for test suites and individual tests

  def build_results(duration, example_count, failure_count, pending_count)
    @builder.instruct! :xml, :version => "1.0", :encoding => "UTF-8"
    @builder.testsuites(
        :errors    => 0,
        :failures  => failure_count,
        :skipped   => pending_count,
        :tests     => example_count,
        :time      => duration,
        :timestamp => Time.now.iso8601) do
      build_all_suites
    end
  end

  def build_all_suites
    @test_suite_results.each do |suite_name, tests|
      build_test_suite(suite_name, tests)
    end
  end

  def build_test_suite(suite_name, tests)
    failure_count = JunitFormatter.count_in_suite_of_type(tests, :failed)
    skipped_count = JunitFormatter.count_in_suite_of_type(tests, :pending)

    @builder.testsuite(
        :name     => suite_name,
        :tests    => tests.size,
        :errors   => 0,
        :failures => failure_count,
        :skipped  => skipped_count) do
      @builder.properties
      build_all_tests tests
    end
  end

  def build_all_tests(tests)
    tests.each do |test|
      build_test test
    end
  end

  def build_test(test)
    test_name      = test.metadata[:description]
    execution_time = test.metadata[:execution_result].run_time
    test_status    = test.metadata[:execution_result].status

    @builder.testcase(:name => test_name, :time => execution_time) do
      case test_status
        when :pending
          @builder.skipped
        when :failed
          build_failed_test test
      end
    end
  end

  def build_failed_test(test)
    failure_message = "failed #{test.metadata[:description]}"

    @builder.failure(:message => failure_message, :type => 'failed') do
      @builder.cdata!(failure_details_for(test).gsub(/\x1b\[\d{1,2}m/,''))
    end
  end

end