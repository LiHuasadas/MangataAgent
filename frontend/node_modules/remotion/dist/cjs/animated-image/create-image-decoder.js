"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createImageDecoder = void 0;
const createImageDecoder = async ({ resolvedSrc, signal, requestInit, contentType, }) => {
    var _a;
    if (typeof ImageDecoder === 'undefined') {
        throw new Error('Your browser does not support the WebCodecs ImageDecoder API.');
    }
    const response = await fetch(resolvedSrc, { ...requestInit, signal });
    const { body } = response;
    if (!body) {
        throw new Error('Got no body');
    }
    const decoder = new ImageDecoder({
        data: body,
        type: (_a = contentType !== null && contentType !== void 0 ? contentType : response.headers.get('Content-Type')) !== null && _a !== void 0 ? _a : 'image/gif',
    });
    await Promise.all([decoder.completed, decoder.tracks.ready]);
    const { selectedTrack } = decoder.tracks;
    if (!selectedTrack) {
        decoder.close();
        throw new Error('No selected track');
    }
    return { decoder, selectedTrack };
};
exports.createImageDecoder = createImageDecoder;
