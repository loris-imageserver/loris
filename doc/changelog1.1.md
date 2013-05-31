## IIIF Image API 1.1 Change Log

### [Section 2](http://www-sul.stanford.edu/iiif/image-api/1.1/#url_syntax)
 * Clarified definition of the prefix segment of the base URI.
 * __Base URI__ defined. [Section 2.2](http://www-sul.stanford.edu/iiif/image-api/1.1/#info_syntax) recommends that this URI returns the image information _or_ redirects to the image information request URI when dereferenced.

### [Section 5](http://www-sul.stanford.edu/iiif/image-api/1.1/#info)
 * Added `@id` and `@context` properties to make image information in JSON [JSON-LD](http://json-ld.org/) compatible. The addition of the base URI in the `@id` property should make it easier for clients to get around XSS/SOP issues when working with IIIF image servers in different domains.
 * Image information in XML (`http[s]://server/[prefix/]identifier/info.xml`) and related schemas deprecated.
 * Clarified the definition of `scale_factors`.

### [Section 6.2](http://www-sul.stanford.edu/iiif/image-api/1.1/#error)
 * Error condition XML response  deprecated. It is recommended that the response body contain human-readable information for development and debugging purposes.
 * Re-defined when a `414` error code should be returned. Implementations may add non-normative features that require query parameters, so the previous explanation was not accurate.

Other minor informative clarifications and non-normative corrections were made throughout.