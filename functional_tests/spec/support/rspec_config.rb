RSpec.configure do |config|

  # Color console output
  config.tty = true

  # Providing access to spec context from within spec
  config.before(:each) do |spec|
    @spec = spec.metadata
  end

  # Prohibit running no_prod tests against PROD
  config.before(:example, :no_prod) do
    skip('Environment is PRODUCTION and this test is marked ":no_production"') if ENVIRONMENT == 'prod'
  end

  # Prohibit running no_test tests against TEST
  config.before(:example, :no_stage) do
    skip('Environment is STAGE and this test is marked ":no_stage"') if ENVIRONMENT == 'stage'
  end

  config.before(:example, :wip) do
    skip('Cases marked ":wip" would not execute.')
  end

  config.before(:example, :no_direct) do
    skip('Cases marked ":no_direct" skipped when execute with direct_service') if DIRECT_SERVICE != ''
  end

end