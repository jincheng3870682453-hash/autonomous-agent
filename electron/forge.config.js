const path = require('path');

module.exports = {
  packagerConfig: {
    asar: true,
    name: 'AutonomousAgent',
  },
  rebuildConfig: {},
  makers: [
    {
      name: '@electron-forge/maker-zip',
      platforms: ['win32'],
      config: {
        name: 'AutonomousAgent'
      }
    }
  ],
  plugins: []
};
