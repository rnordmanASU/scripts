function addModalRelatedObservers() {
    if (window.hasOwnProperty('$addedOverlayObserver')) return;
    window.$addedOverlayObserver = true;

    // Observer to detect when a lightning-overlay-container is inserted in DOM
    const observer = new MutationObserver(function (mutations) {
        // When a lightning-overlay-container is added to DOM, add the slds-scope class to the container
        const overlayContainers = document.querySelectorAll('lightning-overlay-container:not(.slds-scope)');
        for (let i = 0; i < overlayContainers.length; i++) {
            const overlayContainer = overlayContainers[i];

            // add the slds scope class to ensure SLDS styling
            overlayContainer.classList.add('slds-scope');
        }
    });
    
    // Watch page to look out for lightning-overlay-container being added
    observer.observe(
        document.querySelector('body'),
        { 
            attributes: false,
            childList: true,
            characterData: false,
            subtree: false
        }
    );
}

