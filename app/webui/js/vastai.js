// ==============================
// VastAI Legacy Compatibility Layer
// ==============================
// 
// This file provides backward compatibility while transitioning to the modular system.
// The new modular system is in vastai-modular.js and the vastai/ directory.
//
// MIGRATION NOTICE: This legacy file will be deprecated. 
// Please use the new modular API: window.VastAIInstances, window.VastAITemplates, etc.
//

console.log('⚠️  VastAI Legacy Compatibility Layer loaded');
console.log('📄 New modular system available as window.VastAI* modules');

// This compatibility layer will be populated by vastai-modular.js
// The functions below are placeholders that will be overridden

function showMigrationWarning(functionName) {
  console.warn(`⚠️  ${functionName} called from legacy layer. Consider using modular API.`);
}

// Legacy function stubs - these will be overridden by the modular system
window.testVastAISSH = window.testVastAISSH || function() { 
  showMigrationWarning('testVastAISSH'); 
  return Promise.resolve();
};

window.setUIHome = window.setUIHome || function() { 
  showMigrationWarning('setUIHome'); 
  return Promise.resolve();
};

window.getUIHome = window.getUIHome || function() { 
  showMigrationWarning('getUIHome'); 
  return Promise.resolve();
};

window.terminateConnection = window.terminateConnection || function() { 
  showMigrationWarning('terminateConnection'); 
  return Promise.resolve();
};

window.setupCivitDL = window.setupCivitDL || function() { 
  showMigrationWarning('setupCivitDL'); 
  return Promise.resolve();
};

window.syncFromConnectionString = window.syncFromConnectionString || function() { 
  showMigrationWarning('syncFromConnectionString'); 
  return Promise.resolve();
};

window.loadVastaiInstances = window.loadVastaiInstances || function() { 
  showMigrationWarning('loadVastaiInstances'); 
  return Promise.resolve();
};

window.useInstance = window.useInstance || function() { 
  showMigrationWarning('useInstance'); 
};

window.refreshInstanceCard = window.refreshInstanceCard || function() { 
  showMigrationWarning('refreshInstanceCard'); 
  return Promise.resolve();
};

window.showInstanceDetails = window.showInstanceDetails || function() { 
  showMigrationWarning('showInstanceDetails'); 
  return Promise.resolve();
};

window.onTemplateChange = window.onTemplateChange || function() { 
  showMigrationWarning('onTemplateChange'); 
  return Promise.resolve();
};

window.executeTemplateStep = window.executeTemplateStep || function() { 
  showMigrationWarning('executeTemplateStep'); 
  return Promise.resolve();
};

window.loadTemplates = window.loadTemplates || function() { 
  showMigrationWarning('loadTemplates'); 
  return Promise.resolve();
};

window.openSearchOffersModal = window.openSearchOffersModal || function() { 
  showMigrationWarning('openSearchOffersModal'); 
};

window.closeSearchOffersModal = window.closeSearchOffersModal || function() { 
  showMigrationWarning('closeSearchOffersModal'); 
};

window.searchVastaiOffers = window.searchVastaiOffers || function() { 
  showMigrationWarning('searchVastaiOffers'); 
  return Promise.resolve();
};

window.clearSearchResults = window.clearSearchResults || function() { 
  showMigrationWarning('clearSearchResults'); 
};

window.viewOfferDetails = window.viewOfferDetails || function() { 
  showMigrationWarning('viewOfferDetails'); 
};

window.createInstanceFromOffer = window.createInstanceFromOffer || function() { 
  showMigrationWarning('createInstanceFromOffer'); 
  return Promise.resolve();
};

// Debug functions
window.debugTemplateState = window.debugTemplateState || function() { 
  showMigrationWarning('debugTemplateState'); 
  return {};
};

window.testSetUIHomeButton = window.testSetUIHomeButton || function() { 
  showMigrationWarning('testSetUIHomeButton'); 
};

window.debugButtonGeneration = window.debugButtonGeneration || function() { 
  showMigrationWarning('debugButtonGeneration'); 
};

// Utility functions
window.fmtMoney = window.fmtMoney || function(n) {
  if (n === null || n === undefined || isNaN(n)) return "$0/hr";
  return `$${(+n).toFixed(3)}/hr`;
};

window.fmtGb = window.fmtGb || function(v) {
  if (v === null || v === undefined || isNaN(v)) return "0 GB";
  return `${(+v).toFixed(v < 10 ? 2 : 1)} GB`;
};

window.normStatus = window.normStatus || function(s) {
  if (!s) return "unknown";
  const t = String(s).toLowerCase();
  if (["running", "active", "started"].some(k => t.includes(k))) return "running";
  if (["stopped", "terminated", "off"].some(k => t.includes(k))) return "stopped";
  if (["starting", "pending", "init"].some(k => t.includes(k))) return "starting";
  return t;
};

window.showSetupResult = window.showSetupResult || function(message, type) {
  console.log(`📢 showSetupResult: "${message}" (${type})`);
  const resultDiv = document.getElementById('setup-result');
  if (!resultDiv) return;
  
  resultDiv.textContent = message;
  resultDiv.className = `setup-result ${type || 'info'}`;
  resultDiv.style.display = 'block';
};

console.log('✅ VastAI Legacy Layer initialized');

