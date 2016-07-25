function fadeouthandler() {
	this.slide++;
	this.handle = loadhandler;
	this.dom.style.animationPlayState = 'running';
	// For older WebKit browsers
	this.dom.style.webkitAnimationPlayState = 'running';
}

function delayhandler() {
	var state = this;
	setTimeout(function() {
		state.handle = fadeouthandler;
		state.handle();
	}, this.time);
}

function fadeinhandler() {
	this.handle = delayhandler;
	this.dom.style.animationPlayState = 'running';
	// For older WebKit browsers
	this.dom.style.webkitAnimationPlayState = 'running';
}

function loadhandler() {
	var state = this;
	var req = new XMLHttpRequest();
	req.onload = function() {
		if (this.status == 200) {
			state.dom.innerHTML = this.responseText;
		} else {
			if (state.debug) {
				state.dom.innerHTML = this.responseText;
			} else {
				state.dom.innerHTML = "Load error: " + this.statusText;
			}
		}
		state.handle = fadeinhandler;
		state.handle();
	};
	req.open('get', this.url + this.slide, true);
	req.send();
}

function emptyhandler() {
	var state = this;
	this.dom.addEventListener('animationiteration', function() {
		state.dom.style.animationPlayState = 'paused';
		state.handle();
	}, false);
	// For older WebKit browsers
	this.dom.addEventListener('webkitAnimationIteration', function() {
		state.dom.style.webkitAnimationPlayState = 'paused';
		state.handle();
	}, false);
	// maybe also capture animationend?
	this.dom.style.opacity = 0.0;
	this.handle = loadhandler;
	this.handle();
}

function loadpage(url, dom, time) {
	var state = {
		slide: 0,
		url: url,
		dom: dom,
		time: time * 1000,
		handle: emptyhandler,
		debug: true,
	};
	state.handle();
}
