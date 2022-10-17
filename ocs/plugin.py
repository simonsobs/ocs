package_name = 'ocs'
agents = {
    'RegistryAgent': {'module': 'ocs.agents.registry.agent', 'entry_point': 'main'},
    'AggregatorAgent': {'module': 'ocs.agents.aggregator.agent', 'entry_point': 'main'},
    'HostManager': {'module': 'ocs.agents.host_manager.agent', 'entry_point': 'main'},
    'FakeDataAgent': {'module': 'ocs.agents.fake_data.agent', 'entry_point': 'main'},
    'InfluxDBAgent': {'module': 'ocs.agents.influxdb_publisher.agent', 'entry_point': 'main'},
    'BarebonesAgent': {'module': 'ocs.agents.barebones.agent', 'entry_point': 'main'},
}
