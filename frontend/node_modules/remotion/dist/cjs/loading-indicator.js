"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Loading = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const AbsoluteFillElement_js_1 = require("./AbsoluteFillElement.js");
const use_current_scale_js_1 = require("./use-current-scale.js");
const rotate = {
    transform: `rotate(90deg)`,
};
const ICON_SIZE = 40;
const LABEL_SIZE = 14;
const label = {
    color: 'rgba(255, 255, 255, 0.8)',
    fontFamily: 'sans-serif',
};
const container = {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1f2428',
};
const content = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    animation: 'anim 2s',
    animationFillMode: 'forwards',
};
const Loading = () => {
    const scale = (0, use_current_scale_js_1.useCurrentScale)({ dontThrowIfOutsideOfRemotion: true });
    return (jsx_runtime_1.jsxs(AbsoluteFillElement_js_1.AbsoluteFillElement, { style: container, id: "remotion-comp-loading", children: [
            jsx_runtime_1.jsx("style", { type: "text/css", children: `
				@keyframes anim {
					from {
						opacity: 0
					}
					to {
						opacity: 1
					}
				}
			` }), jsx_runtime_1.jsxs("div", { id: "remotion-comp-loading-content", style: content, children: [
                    jsx_runtime_1.jsx("svg", { width: ICON_SIZE / scale, height: ICON_SIZE / scale, viewBox: "-100 -100 400 400", style: rotate, children: jsx_runtime_1.jsx("path", { fill: "#555", stroke: "#555", strokeWidth: "100", strokeLinejoin: "round", d: "M 2 172 a 196 100 0 0 0 195 5 A 196 240 0 0 0 100 2.259 A 196 240 0 0 0 2 172 z" }) }), jsx_runtime_1.jsxs("p", { style: { ...label, fontSize: LABEL_SIZE / scale }, children: ["Resolving ", '<Suspense>', "..."] })
                ] })
        ] }));
};
exports.Loading = Loading;
