import setuptools

setuptools.setup(
    name="muistotkartalla",
    version="0.0.1",
    author="TEST ONLY",
    author_email="TEST ONLY",
    description="TEST ONLY",
    long_description="TEST ONLY",
    long_description_content_type="text/markdown",
    url="TEST ONLY",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(include=["muistot", "muistot.*"]),
    python_requires=">=3.9",
    package_data={
        'muistot.mailer.templates': ['*.html']
    },
)
