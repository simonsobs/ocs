package_name = 'ocs'
agents = {
  'RegistryAgent': {'module': 'ocs.agents.registry', 'entry_point': 'main'},
  'AggregatorAgent': {'module': 'ocs.agents.aggregator_agent', 'entry_point': 'main'},
  'HostManager': {'module': 'ocs.agents.host_manager', 'entry_point': 'main'},
  'FakeDataAgent': {'module': 'ocs.agents.fake_data_agent', 'entry_point': 'main'},
  'InfluxDBAgent': {'module': 'ocs.agents.influxdb_publisher', 'entry_point': 'main'},
  'BarebonesAgent': {'module': 'ocs.agents.barebones_agent', 'entry_point': 'main'},
}
