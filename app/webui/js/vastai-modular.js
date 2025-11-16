// ==============================
// VastAI Main Module - Entry Point
// ==============================
// 
// Modular VastAI system - Version 3.0
// This file coordinates all VastAI modules and exposes APIs to the global scope
//

console.log('📄 VastAI Main - Version 3.0 (Modular) loading...');

// Import all modules
import * as VastAIUtils from './vastai/utils.js';
import * as VastAIUI from './vastai/ui.js';
import * as VastAIInstances from './vastai/instances.js';
import * as VastAITemplates from './vastai/templates.js';
import * as VastAISearch from './vastai/search.js';

// Create module namespaces for organized access
window.VastAIUtils = VastAIUtils;
window.VastAIUI = VastAIUI;
window.VastAIInstances = VastAIInstances;
window.VastAITemplates = VastAITemplates;
window.VastAISearch = VastAISearch;

// Expose commonly used functions to global scope for backward compatibility
// and ease of use in HTML onclick handlers

// === INSTANCE MANAGEMENT ===
window.testVastAISSH = VastAIInstances.testVastAISSH;
window.setUIHome = VastAIInstances.setUIHome;
window.getUIHome = VastAIInstances.getUIHome;
window.terminateConnection = VastAIInstances.terminateConnection;
window.setupCivitDL = VastAIInstances.setupCivitDL;
window.testCivitDL = VastAIInstances.testCivitDL;
window.setupPythonVenv = VastAIInstances.setupPythonVenv;
window.cloneAutoInstaller = VastAIInstances.cloneAutoInstaller;
window.syncFromConnectionString = VastAIInstances.syncFromConnectionString;
window.loadVastaiInstances = VastAIInstances.loadVastaiInstances;
window.useInstance = VastAIInstances.useInstance;
window.refreshInstanceCard = VastAIInstances.refreshInstanceCard;
window.stopInstance = VastAIInstances.stopInstance;
window.destroyInstance = VastAIInstances.destroyInstance;

// === UI COMPONENTS ===
window.showSetupResult = VastAIUI.showSetupResult;
window.showInstanceDetails = VastAIUI.showInstanceDetails;
window.openSearchOffersModal = VastAIUI.openSearchOffersModal;
window.closeSearchOffersModal = VastAIUI.closeSearchOffersModal;

// === TEMPLATE MANAGEMENT ===
window.onTemplateChange = VastAITemplates.onTemplateChange;
window.executeTemplateStep = VastAITemplates.executeTemplateStep;
window.loadTemplates = VastAITemplates.loadTemplates;

// === SEARCH FUNCTIONALITY ===
window.searchVastaiOffers = VastAISearch.searchVastaiOffers;
window.clearSearchResults = VastAISearch.clearSearchResults;
window.viewOfferDetails = VastAISearch.viewOfferDetails;
window.createInstanceFromOffer = VastAISearch.createInstanceFromOffer;

// === DEBUG FUNCTIONS ===
window.debugTemplateState = VastAITemplates.debugTemplateState;
window.testSetUIHomeButton = VastAITemplates.testSetUIHomeButton;
window.debugButtonGeneration = VastAITemplates.debugButtonGeneration;

// === UTILITY FUNCTIONS ===
window.fmtMoney = VastAIUtils.fmtMoney;
window.fmtGb = VastAIUtils.fmtGb;
window.normStatus = VastAIUtils.normStatus;
window.resolveSSH = VastAIUtils.resolveSSH;

/**
 * Initialize VastAI system
 * Called when the DOM is ready
 */
function initializeVastAI() {
  console.log('🔧 Initializing VastAI system...');
  
  // Initialize templates on page load
  VastAITemplates.loadTemplates();
  
  console.log('✅ VastAI system initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeVastAI);
} else {
  // DOM is already ready
  initializeVastAI();
}

// Debug helper to show module structure
window.VastAIDebug = {
  modules: {
    Utils: Object.keys(VastAIUtils),
    UI: Object.keys(VastAIUI),
    Instances: Object.keys(VastAIInstances),
    Templates: Object.keys(VastAITemplates),
    Search: Object.keys(VastAISearch)
  },
  showStructure() {
    console.log('🔧 VastAI Module Structure:');
    Object.entries(this.modules).forEach(([moduleName, functions]) => {
      console.log(`📦 ${moduleName}:`, functions);
    });
    return this.modules;
  }
};

console.log('✅ VastAI Main - Version 3.0 (Modular) loaded successfully');
console.log('🎯 Use VastAIDebug.showStructure() to see all available functions');

export { VastAIUtils, VastAIUI, VastAIInstances, VastAITemplates, VastAISearch };