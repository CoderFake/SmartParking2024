

var autoprefixer = require('gulp-autoprefixer');
var browserSync = require('browser-sync').create();
var cleanCss = require('gulp-clean-css');
var gulp = require('gulp');
const npmDist = require('gulp-npm-dist');
var sass = require('gulp-sass')(require('sass'));
var wait = require('gulp-wait');
var sourcemaps = require('gulp-sourcemaps');
var rename = require("gulp-rename");

const ignore = require('gulp-ignore');

const paths = {
    src: {
        base: './',
        css: './css',
        scss: './scss',
        node_modules: './node_modules/',
        vendor: './vendor'
    }
};

gulp.task('scss', function() {
    return gulp.src([
            paths.src.scss + '/custom/**/*.scss',
            paths.src.scss + '/volt/**/*.scss',
            paths.src.scss + '/volt.scss',
            '!**/node_modules/**'
        ])
        .pipe(wait(500))
        .pipe(sourcemaps.init())
        .pipe(sass().on('error', sass.logError))
        .pipe(autoprefixer({
            overrideBrowserslist: ['> 1%']
        }))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(paths.src.css))
        .pipe(browserSync.stream());
});

// Minify CSS
gulp.task('minify:css', function() {
    return gulp.src([
            paths.src.css + '/volt.css',
            '!**/node_modules/**'
        ])
        .pipe(cleanCss())
        .pipe(rename(function(path) {
            path.extname = ".min.css";
        }))
        .pipe(gulp.dest(paths.src.css))
});

// Default Task: Compile SCSS and minify the result
gulp.task('default', gulp.series('scss', 'minify:css'));