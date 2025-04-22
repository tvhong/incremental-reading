/*
 * Copyright 2023 
 *
 * Permission to use, copy, modify, and distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
 * SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION
 * OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
 * CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

function createTableOfContents() {
    addTOCStyles();
    
    // Use setTimeout to ensure DOM is fully loaded
    setTimeout(() => {
        const isIrCard = document.querySelector('.card') !== null;
        
        if (isIrCard) {
            const tocItems = parseHeadings();
            addTocContainerElement(tocItems);
            makeTocDraggable();
        }
    }, 500);
}

// Add CSS styles for TOC
function addTOCStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .ir-toc-container {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 250px;
            max-height: 80vh;
            margin: auto; /* Needed so ToC container doesn't drop when dragged */
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            z-index: 1000;
            overflow-y: auto;
            font-size: 14px;
            opacity: 0.5;
            transition: opacity 0.3s;
        }
        
        .ir-toc-container:hover {
            opacity: 1;
        }
        
        .ir-toc-header {
            margin: auto;
            padding-left: 15px;
            padding-right: 10px;
            background-color: #f5f5f5;
            border-bottom: 1px solid #ddd;
            display: flex;
            font-size: 16px;
            justify-content: space-between;
            align-items: center;
            cursor: move;
            font-weight: bold;
        }
        
        #ir-toc-toggle {
            background: none;
            border: none;
            font-size: 16px;
            cursor: pointer;
            width: 20px;
            height: 20px;
            padding: 0;
            line-height: 1;
        }
        
        .ir-toc-content {
            margin: auto;
            padding: 10px;
        }
        
        .ir-toc-list {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        
        .ir-toc-item {
            margin: 5px 0;
        }
        
        .ir-toc-item a {
            text-decoration: none;
            color: #333;
            display: block;
            padding: 2px 0;
        }
        
        .ir-toc-item a:hover {
            color: #3498db;
        }
        
        .ir-toc-level-h1 { margin-left: 0; }
        .ir-toc-level-h2 { margin-left: 10px; }
        .ir-toc-level-h3 { margin-left: 20px; }
        .ir-toc-level-h4 { margin-left: 30px; }
        .ir-toc-level-h5 { margin-left: 40px; }
        .ir-toc-level-h6 { margin-left: 50px; }
    `;
    
    document.head.appendChild(style);
}

function parseHeadings() {
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    if (headings.length === 0) {
        return null;
    }

    const tocItems = [];
    headings.forEach((heading, index) => {
        // Add IDs if doesn't exist, so we can link to it
        if (!heading.id) {
            heading.id = 'toc-heading-' + index;
        }
        
        tocItems.push({
            id: heading.id,
            text: heading.textContent,
            level: heading.tagName.toLowerCase()
        });
    });

    return tocItems;
}

function addTocContainerElement(tocItems) {
    if (!tocItems) {
        return false;
    }

    const tocContainer = createTocContainerElement();
    
    const tocHeader = createTocHeaderElement();
    tocContainer.appendChild(tocHeader);
    
    const tocContent = createTocContentElement(tocItems);
    tocContainer.appendChild(tocContent);
    
    document.body.appendChild(tocContainer);
    
    return true;
}

function createTocContainerElement() {
    const container = document.createElement('div');
    container.id = 'ir-toc-container';
    container.className = 'ir-toc-container';
    return container;
}

function createTocHeaderElement() {
    const header = document.createElement('div');
    header.className = 'ir-toc-header';
    header.innerHTML = '<span>TOC</span><button id="ir-toc-toggle">−</button>';
    
    const toggleButton = header.querySelector('#ir-toc-toggle');
    toggleButton.addEventListener('click', function() {
        const tocContent = document.getElementById('ir-toc-content');
        const isVisible = tocContent.style.display !== 'none';
        
        if (isVisible) {
            tocContent.style.display = 'none';
            this.textContent = '+';
        } else {
            tocContent.style.display = 'block';
            this.textContent = '−';
        }
    });

    
    return header;
}

function createTocContentElement(tocItems) {
    const tocContent = document.createElement('div');
    tocContent.id = 'ir-toc-content';
    tocContent.className = 'ir-toc-content';
    
    const tocList = document.createElement('ul');
    tocList.className = 'ir-toc-list';
    
    tocItems.forEach(item => {
        const tocItem = document.createElement('li');
        tocItem.className = 'ir-toc-item ir-toc-level-' + item.level;
        
        tocItem.appendChild(createItemLinkElement(item));
        tocList.appendChild(tocItem);
    });
    
    tocContent.appendChild(tocList);
    return tocContent;
}

function createItemLinkElement(item) {
    const link = document.createElement('a');
    link.href = '#' + item.id;
    link.textContent = item.text;
    link.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Scroll to heading with a slight offset
        const targetHeading = document.getElementById(item.id);
        const topOffset = targetHeading.getBoundingClientRect().top + window.scrollY - 20;
        window.scrollTo({
            top: topOffset,
            behavior: 'smooth'
        });
    });

    return link;
}

function makeTocDraggable() {
    const tocContainer = document.getElementById('ir-toc-container');
    const tocHeader = document.querySelector('.ir-toc-header');
    
    let isDragging = false;
    let initialX, initialY, initialMouseX, initialMouseY;
    
    tocHeader.addEventListener('mousedown', function(e) {
        e.preventDefault(); // Prevent text selection during drag
        isDragging = true;
        
        initialX = tocContainer.offsetLeft;
        initialY = tocContainer.offsetTop;
        initialMouseX = e.clientX;
        initialMouseY = e.clientY;
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        
        e.preventDefault();
        
        const deltaX = e.clientX - initialMouseX;
        const deltaY = e.clientY - initialMouseY;
        
        tocContainer.style.left = (initialX + deltaX) + 'px';
        tocContainer.style.top = (initialY + deltaY) + 'px';
        tocContainer.style.right = 'auto';
    });
    
    document.addEventListener('mouseup', function(e) {
        isDragging = false;
    });
}

// Hook into Anki's onUpdateHook
onUpdateHook.push(createTableOfContents);
